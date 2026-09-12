#!/usr/bin/env python3
"""Failure-aware aggregate for future semantic protocol replications."""
from __future__ import annotations
import argparse, importlib.util, json, sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
BASE=load("semantic_aggregate_v2_base",ROOT/"benchmarks/semantic_protocol.py");MODEL=BASE.MODEL

def summarize(rows):
    accepted=sum(row["accepted"] for row in rows);total=sum(row["metrics"]["total_tokens"] for row in rows)
    failures=Counter(
        "accepted" if row["accepted"] else (
            (row.get("failure") or {}).get("classification")
            or (row.get("failure") or {}).get("phase")
            or "unknown_failure"
        )
        for row in rows
    )
    return {"trials":len(rows),"accepted":accepted,"failed":len(rows)-accepted,"acceptance_rate":accepted/len(rows) if rows else None,"compile_at_1_rate":sum(row["compile_at_1"] for row in rows)/len(rows) if rows else None,"pass_at_1_rate":sum(row["pass_at_1"] for row in rows)/len(rows) if rows else None,"total_provider_tokens":total,"total_tokens_per_accepted_solution":total/accepted if accepted else None,"not_estimable_reason":"zero_accepted_trials" if rows and not accepted else None,"repair_rounds_total":sum(row["repair_rounds"] for row in rows),"failure_classifications":dict(sorted(failures.items()))}

def aggregate_rows(rows):
    names=sorted({row["representation"] for row in rows});categories=sorted({row["category"] for row in rows})
    return {"schema_version":2,"evidence":"measured","trials":len(rows),"representations":[{"representation":name,**summarize([row for row in rows if row["representation"]==name])} for name in names],"categories":[{"category":category,"representation":name,**summarize([row for row in rows if row["category"]==category and row["representation"]==name])} for category in categories for name in names]}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--raw",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    try:document=aggregate_rows(MODEL.read_rows(args.raw));args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(document,indent=2,sort_keys=True)+"\n")
    except (MODEL.ModelBenchmarkError,OSError) as error:print(f"aggregate error: {error}",file=sys.stderr);return 2
    return 0
if __name__=="__main__":raise SystemExit(main())
