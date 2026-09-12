#!/usr/bin/env python3
"""Render the frozen semantic-protocol-v1 comparison as Markdown."""
import argparse,json
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument("--comparison",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();d=json.loads(a.comparison.read_text());primary=d["primary"]
    def line(v):
        l=v["left_result"];r=v["right_result"];diff=v["difference"]
        return f"| {v['left']} vs {v['right']} | {l['accepted']}/{l['trials']} | {r['accepted']}/{r['trials']} | {l['total_tokens_per_accepted_solution']:.2f} | {r['total_tokens_per_accepted_solution']:.2f} | {diff['total_tokens_per_accepted_solution']:.2f} | {v['status']} |"
    lines=["# Semantic protocol v1 results","",f"Decision: `{d['decision']['classification']}`.","","All numbers below are provider-measured; failed attempts remain in the numerator.","","| Comparison | Left accepted | Right accepted | Left tokens/accepted | Right tokens/accepted | Difference | Status |","|---|---:|---:|---:|---:|---:|---|",line(primary),*[line(v) for v in d["exploratory"]],"","The ordinary comparison is confirmatory. Python, Go, and Rust comparisons are exploratory system comparisons and cannot establish a source-language effect.",""]
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text("\n".join(lines));return 0
if __name__=="__main__":raise SystemExit(main())
