#!/usr/bin/env python3
"""Supplement frozen semantic analysis when a comparator has zero accepted trials.

The preregistered comparator is preserved byte-for-byte. This compatibility
analysis applies its unchanged primary decision rule and marks token metrics for
zero-acceptance comparators as not estimable.
"""
from __future__ import annotations
import argparse, importlib.util, json, sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
CMP=load("semantic_frozen_compare_postrun",ROOT/"benchmarks/semantic_protocol_compare.py"); MODEL=CMP.MODEL
def grouped(rows):
    result={}
    for row in rows:result.setdefault(row["case_id"],{}).setdefault(row["representation"],[]).append(row)
    return result
def unestimable(by_case,left,right):
    left_rows=[r for case in by_case.values() for r in case[left]];right_rows=[r for case in by_case.values() for r in case[right]]
    categories=[]
    for category in sorted({r["category"] for r in left_rows}):
        a=[r for r in left_rows if r["category"]==category];b=[r for r in right_rows if r["category"]==category]
        categories.append({"category":category,"left":CMP.compact(a),"right":CMP.compact(b),"token_difference":None})
    return {"left":left,"right":right,"confirmatory":False,"left_result":CMP.compact(left_rows),"right_result":CMP.compact(right_rows),"difference":{"total_tokens_per_accepted_solution":None,"acceptance_rate":CMP.rate(left_rows)-CMP.rate(right_rows),"case_cluster_bootstrap_95_percent_interval":None,"one_sided_token_upper":None,"acceptance_interval":None,"samples":0,"seed":None},"noninferiority":{"comparator_accepted_cases":0,"left_loss_cases":0,"observed_loss_rate":None,"one_sided_exact_upper":None,"limit":.05},"categories":categories,"status":"not_estimable_zero_comparator_acceptance"}
def breakdown(rows):
    result=[]
    for name in CMP.RUN.REPRESENTATIONS:
        values=[r for r in rows if r["representation"]==name];attempts=[a for r in values for a in r["attempts"]];repairs=[a for r in values for a in r["attempts"][1:]]
        phases=Counter((r["failure"] or {}).get("phase","accepted") for r in values)
        first= [r["attempts"][0]["context_bytes"] for r in values]
        result.append({"representation":name,"trials":len(values),"accepted":sum(r["accepted"] for r in values),"api_calls":len(attempts),"repair_calls":len(repairs),"provider_usage":{field:sum(a["usage"][field] for a in attempts) for field in ("input_tokens","output_tokens","total_tokens","cached_input_tokens","reasoning_tokens")},"repair_provider_usage":{field:sum(a["usage"][field] for a in repairs) for field in ("input_tokens","output_tokens","total_tokens","cached_input_tokens","reasoning_tokens")},"first_attempt_context_utf8_bytes":{field:sum(x[field] for x in first) for field in ("instruction_bytes","prompt_template_bytes","specification_bytes","repository_context_bytes","task_bytes","initial_diagnostic_bytes")},"final_outcomes":dict(sorted(phases.items()))})
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument("--raw",type=Path,required=True);p.add_argument("--comparison",type=Path,required=True);p.add_argument("--breakdown",type=Path,required=True);p.add_argument("--report",type=Path,required=True);a=p.parse_args();rows=MODEL.read_rows(a.raw);by=grouped(rows)
    primary=CMP.compare_pair(by,"tacitra-semantic","tacitra-ordinary",20000,20260913,True)
    exploratory=[CMP.compare_pair(by,"tacitra-semantic","python-ordinary",20000,20260914,False),CMP.compare_pair(by,"tacitra-semantic","go-ordinary",20000,20260915,False),unestimable(by,"tacitra-semantic","rust-ordinary")]
    decision="supports_semantic_protocol" if primary["status"]=="supports_advantage" else "does_not_support_semantic_protocol" if primary["status"]=="does_not_support" else "inconclusive"
    document={"schema_version":1,"evidence":"measured","analysis":"postrun-zero-acceptance-compatibility","frozen_comparator_revision":MODEL.sha256((ROOT/"benchmarks/semantic_protocol_compare.py").read_bytes()),"compatibility_processor_revision":MODEL.sha256(Path(__file__).read_bytes()),"frozen_comparator_failure":"IndexError on empty token bootstrap for rust-ordinary with zero accepted trials","primary":primary,"exploratory":exploratory,"decision":{"classification":decision},"limitations":["Primary comparison and decision rule are unchanged from preregistration.","Rust token-per-accepted and token-difference metrics are not estimable because Rust accepted zero trials.","This compatibility processor was not preregistered and is identified as post-run analysis.","The frozen harness context_bytes metadata uses AGENTS.md size for ordinary conditions although requests used the smaller pinned persistent instructions; provider usage is unaffected.","Stateless repair requests resend their initial prompt before the minimal repair object, so minimal-repair causal savings are not isolated."]}
    detail={"schema_version":1,"evidence":"measured","representations":breakdown(rows)}
    a.comparison.parent.mkdir(parents=True,exist_ok=True);a.comparison.write_text(json.dumps(document,indent=2,sort_keys=True)+"\n");a.breakdown.write_text(json.dumps(detail,indent=2,sort_keys=True)+"\n")
    def fmt(value):return "not estimable" if value is None else f"{value:.2f}"
    lines=["# Semantic protocol v1 results","",f"Preregistered decision: `{decision}`.","","> The frozen comparator stopped on Rust's zero accepted trials. The primary rule is unchanged; this report uses an identified post-run compatibility processor and marks Rust token-per-accepted metrics as not estimable.","","| Comparison | Left accepted | Right accepted | Left tokens/accepted | Right tokens/accepted | Difference | Status |","|---|---:|---:|---:|---:|---:|---|"]
    for value in [primary,*exploratory]:
        l=value["left_result"];r=value["right_result"];d=value["difference"]["total_tokens_per_accepted_solution"];lines.append(f"| {value['left']} vs {value['right']} | {l['accepted']}/{l['trials']} | {r['accepted']}/{r['trials']} | {fmt(l['total_tokens_per_accepted_solution'])} | {fmt(r['total_tokens_per_accepted_solution'])} | {fmt(d)} | {value['status']} |")
    lines += ["","## Provider-token totals","","| Representation | Total | Input | Visible output | Reasoning | Cached | Repair calls | Repair total |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    for value in detail["representations"]:
        u=value["provider_usage"];repair=value["repair_provider_usage"];visible=u["output_tokens"]-u["reasoning_tokens"]
        lines.append(f"| {value['representation']} | {u['total_tokens']} | {u['input_tokens']} | {visible} | {u['reasoning_tokens']} | {u['cached_input_tokens']} | {value['repair_calls']} | {repair['total_tokens']} |")
    lines += ["","## Category results","","| Category | Semantic accepted | Ordinary accepted | Semantic tokens/accepted | Ordinary tokens/accepted | Difference |","|---|---:|---:|---:|---:|---:|"]
    for value in primary["categories"]:
        l=value["left"];r=value["right"];lines.append(f"| {value['category']} | {l['accepted']}/{l['trials']} | {r['accepted']}/{r['trials']} | {fmt(l['total_tokens_per_accepted_solution'])} | {fmt(r['total_tokens_per_accepted_solution'])} | {fmt(value['token_difference'])} |")
    lines += ["","## Interpretation","","- Task capsule + task-scoped specification reduced measured input by 5,142 tokens (12.29%) versus Tacitra ordinary, but this combined system comparison does not isolate the specification alone.","- Compact typed edits averaged 186.05 bytes versus 333.38 ordinary diff bytes. Non-reasoning output was 6,741 versus 7,792 tokens, while semantic reasoning rose to 20,490 versus 4,147 tokens.","- Semantic repair used 11 calls and 11,016 tokens. Its repair-attempt input averaged 629.55 tokens versus 816.50 for two ordinary repairs, but no preregistered repair ablation exists, and stateless requests resend the initial prompt.","- Cached input was zero in every condition. Warm-session values remain static arithmetic projections, not real-model measurements.","- Static development ablations remain the only evidence for individually disabling task-scoped specification, semantic query, and typed patch; they must not be interpreted as model causal effects.","","## Execution limitations","","Rust accepted 0/60 because every compile command failed with `[Errno 2] No such file or directory: 'rustc'`; this is an execution-environment failure, not evidence about Rust generation quality. The raw run is retained and was not rerun. The frozen comparator then failed on the zero-acceptance token denominator; this report's compatibility processor preserves the primary rule and marks Rust token comparisons unestimable.","","Provider totals, category details, repair usage, context-byte classifications, and limitations are retained in the machine-readable aggregate, comparison, and breakdown files.",""]
    a.report.write_text("\n".join(lines));return 0
if __name__=="__main__":raise SystemExit(main())
