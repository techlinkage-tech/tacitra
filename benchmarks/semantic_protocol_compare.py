#!/usr/bin/env python3
"""Preregistered case-cluster comparison for semantic-protocol-v1."""
from __future__ import annotations
import argparse, importlib.util, json, math, random, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module); return module
RUN=load("semantic_runner_compare",ROOT/"benchmarks/semantic_protocol.py"); MODEL=RUN.MODEL

def percentile(values,p):
    values=sorted(values); return values[min(len(values)-1,max(0,round((len(values)-1)*p)))]
def primary(rows):
    accepted=sum(r["accepted"] for r in rows); return None if not accepted else sum(r["metrics"]["total_tokens"] for r in rows)/accepted
def rate(rows,field="accepted"): return sum(bool(r[field]) for r in rows)/len(rows)
def cdf(events,trials,p): return sum(math.comb(trials,k)*p**k*(1-p)**(trials-k) for k in range(events+1))
def upper(events,trials,alpha=.05):
    if not trials:return None
    if events==trials:return 1.0
    lo,hi=0.0,1.0
    for _ in range(80):
        mid=(lo+hi)/2
        if cdf(events,trials,mid)>alpha:lo=mid
        else:hi=mid
    return hi
def compact(rows):
    return {"trials":len(rows),"accepted":sum(r["accepted"] for r in rows),"acceptance_rate":rate(rows),"compile_at_1_rate":rate(rows,"compile_at_1"),"pass_at_1_rate":rate(rows,"pass_at_1"),"total_tokens_per_accepted_solution":primary(rows),"input_tokens":MODEL.metric([r["metrics"]["input_tokens"] for r in rows]),"output_tokens":MODEL.metric([r["metrics"]["output_tokens"] for r in rows]),"cached_input_tokens":MODEL.metric([r["metrics"]["cached_input_tokens"] for r in rows]),"reasoning_tokens":MODEL.metric([r["metrics"]["reasoning_tokens"] for r in rows]),"repair_rounds":MODEL.metric([r["repair_rounds"] for r in rows]),"patch_size":MODEL.metric([r["patch_size"] for r in rows]),"wall_clock_time":MODEL.metric([r["wall_clock_time"] for r in rows])}
def compare_pair(by_case,left,right,samples,seed,confirmatory):
    ids=sorted(by_case); left_rows=[r for cid in ids for r in by_case[cid][left]]; right_rows=[r for cid in ids for r in by_case[cid][right]]
    rng=random.Random(seed); diffs=[]; acceptance=[]
    for _ in range(samples):
        chosen=[ids[rng.randrange(len(ids))] for _ in ids]; a=[r for cid in chosen for r in by_case[cid][left]]; b=[r for cid in chosen for r in by_case[cid][right]]
        if primary(a) is not None and primary(b) is not None:diffs.append(primary(a)-primary(b))
        acceptance.append(rate(a)-rate(b))
    eligible=[cid for cid in ids if all(r["accepted"] for r in by_case[cid][right])]
    losses=sum(not all(r["accepted"] for r in by_case[cid][left]) for cid in eligible); loss_upper=upper(losses,len(eligible))
    categories=[]
    for cat in sorted({r["category"] for r in left_rows}):
        a=[r for r in left_rows if r["category"]==cat]; b=[r for r in right_rows if r["category"]==cat]
        categories.append({"category":cat,"left":compact(a),"right":compact(b),"token_difference":None if primary(a) is None or primary(b) is None else primary(a)-primary(b)})
    token_upper=percentile(diffs,.95); success=(token_upper<0 and loss_upper is not None and loss_upper<=.05 and all(c["left"]["accepted"]>0 for c in categories))
    contradiction=(percentile(diffs,.05)>=0 or (losses/len(eligible) if eligible else 1)>.05)
    return {"left":left,"right":right,"confirmatory":confirmatory,"left_result":compact(left_rows),"right_result":compact(right_rows),"difference":{"total_tokens_per_accepted_solution":primary(left_rows)-primary(right_rows) if primary(left_rows) is not None and primary(right_rows) is not None else None,"acceptance_rate":rate(left_rows)-rate(right_rows),"case_cluster_bootstrap_95_percent_interval":[percentile(diffs,.025),percentile(diffs,.975)],"one_sided_token_upper":token_upper,"acceptance_interval":[percentile(acceptance,.025),percentile(acceptance,.975)],"samples":samples,"seed":seed},"noninferiority":{"comparator_accepted_cases":len(eligible),"left_loss_cases":losses,"observed_loss_rate":None if not eligible else losses/len(eligible),"one_sided_exact_upper":loss_upper,"limit":.05},"categories":categories,"status":"supports_advantage" if success else "does_not_support" if contradiction else "inconclusive"}
def compare(rows,samples,seed):
    if len(rows)!=300:raise MODEL.ModelBenchmarkError(f"expected 300 trials, found {len(rows)}")
    by_case={}
    for row in rows:by_case.setdefault(row["case_id"],{}).setdefault(row["representation"],[]).append(row)
    if len(by_case)!=60 or any(set(v)!=set(RUN.REPRESENTATIONS) or any(len(x)!=1 for x in v.values()) for v in by_case.values()):raise MODEL.ModelBenchmarkError("incomplete case clusters")
    primary_result=compare_pair(by_case,"tacitra-semantic","tacitra-ordinary",samples,seed,True)
    exploratory=[compare_pair(by_case,"tacitra-semantic",name,samples,seed+i+1,False) for i,name in enumerate(("python-ordinary","go-ordinary","rust-ordinary"))]
    return {"schema_version":1,"evidence":"measured","independent_cases":60,"repetitions":1,"total_trials":300,"bootstrap_unit":"case","primary":primary_result,"exploratory":exploratory,"decision":{"classification":"supports_semantic_protocol" if primary_result["status"]=="supports_advantage" else "does_not_support_semantic_protocol" if primary_result["status"]=="does_not_support" else "inconclusive"},"limitations":["Cases are the only independent sampling unit.","Cross-language comparisons are exploratory system comparisons, not language-only effects."]}
def main():
    p=argparse.ArgumentParser(); p.add_argument("--raw",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--bootstrap-samples",type=int,default=20000); p.add_argument("--seed",type=int,default=20260913); a=p.parse_args()
    try:d=compare(MODEL.read_rows(a.raw),a.bootstrap_samples,a.seed); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    except (MODEL.ModelBenchmarkError,OSError) as e:print(f"semantic comparison error: {e}",file=sys.stderr);return 2
    return 0
if __name__=="__main__":raise SystemExit(main())
