#!/usr/bin/env python3
"""Zero-acceptance-safe comparison for future semantic protocol replications."""

from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
LEGACY=load("semantic_compare_v2_legacy",ROOT/"benchmarks/semantic_protocol_compare.py");MODEL=LEGACY.MODEL

def not_estimable(by_case,left,right,confirmatory):
    ids=sorted(by_case);a=[r for cid in ids for r in by_case[cid][left]];b=[r for cid in ids for r in by_case[cid][right]]
    categories=[]
    for category in sorted({r["category"] for r in a}):
        left_rows=[r for r in a if r["category"]==category];right_rows=[r for r in b if r["category"]==category]
        categories.append({"category":category,"left":LEGACY.compact(left_rows),"right":LEGACY.compact(right_rows),"token_difference":None,"not_estimable_reason":"zero_accepted_trials"})
    return {"left":left,"right":right,"confirmatory":confirmatory,"left_result":LEGACY.compact(a),"right_result":LEGACY.compact(b),"difference":{"total_tokens_per_accepted_solution":None,"case_cluster_bootstrap_95_percent_interval":None,"one_sided_token_upper":None,"not_estimable_reason":"zero_accepted_trials"},"categories":categories,"status":"not_estimable","total_tokens_retained":sum(r["metrics"]["total_tokens"] for r in a+b),"failed_trial_tokens_retained":sum(r["metrics"]["total_tokens"] for r in a+b if not r["accepted"]),"failed_trials_retained":sum(not r["accepted"] for r in a+b),"repair_rounds_retained":sum(r["repair_rounds"] for r in a+b)}

def safe_pair(by_case,left,right,samples,seed,confirmatory):
    a=[r for case in by_case.values() for r in case[left]];b=[r for case in by_case.values() for r in case[right]]
    if LEGACY.primary(a) is None or LEGACY.primary(b) is None:return not_estimable(by_case,left,right,confirmatory)
    return LEGACY.compare_pair(by_case,left,right,samples,seed,confirmatory)

def compare(rows,samples,seed):
    by_case={}
    for row in rows:by_case.setdefault(row["case_id"],{}).setdefault(row["representation"],[]).append(row)
    names=LEGACY.RUN.REPRESENTATIONS
    if not by_case or any(set(value)!=set(names) for value in by_case.values()):raise MODEL.ModelBenchmarkError("incomplete comparison clusters")
    primary=safe_pair(by_case,"tacitra-semantic","tacitra-ordinary",samples,seed,True)
    exploratory=[safe_pair(by_case,"tacitra-semantic",name,samples,seed+i+1,False) for i,name in enumerate(("python-ordinary","go-ordinary","rust-ordinary"))]
    classification="inconclusive" if primary["status"]=="not_estimable" else "supports_semantic_protocol" if primary["status"]=="supports_advantage" else "does_not_support_semantic_protocol" if primary["status"]=="does_not_support" else "inconclusive"
    return {"schema_version":2,"evidence":"measured","zero_accepted_policy":{"tokens_per_accepted":None,"differences":None,"intervals":None,"reason":"zero_accepted_trials"},"primary":primary,"exploratory":exploratory,"decision":{"classification":classification}}

def render(document):
    def fmt(value):return "not estimable" if value is None else f"{value:.2f}"
    values=[document["primary"],*document["exploratory"]];lines=["# Semantic protocol replication results","",f"Decision: `{document['decision']['classification']}`.","","| Comparison | Left accepted | Right accepted | Left tokens/accepted | Right tokens/accepted | Difference | Status |","|---|---:|---:|---:|---:|---:|---|"]
    for value in values:
        left=value["left_result"];right=value["right_result"];difference=value["difference"]["total_tokens_per_accepted_solution"]
        lines.append(f"| {value['left']} vs {value['right']} | {left['accepted']}/{left['trials']} | {right['accepted']}/{right['trials']} | {fmt(left['total_tokens_per_accepted_solution'])} | {fmt(right['total_tokens_per_accepted_solution'])} | {fmt(difference)} | {value['status']} |")
    return "\n".join(lines)+"\n"

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--raw",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);parser.add_argument("--report",type=Path);parser.add_argument("--bootstrap-samples",type=int,default=20000);parser.add_argument("--seed",type=int,default=20260913);args=parser.parse_args()
    try:
        document=compare(MODEL.read_rows(args.raw),args.bootstrap_samples,args.seed);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(document,indent=2,sort_keys=True)+"\n")
        if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(render(document))
    except (MODEL.ModelBenchmarkError,OSError) as error:print(f"comparison error: {error}",file=sys.stderr);return 2
    return 0
if __name__=="__main__":raise SystemExit(main())
