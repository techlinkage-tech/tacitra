#!/usr/bin/env python3
"""Frozen semantic-protocol-v1 validation, dry-run, execution and aggregation."""

from __future__ import annotations

import argparse, importlib.util, json, random, sys, tempfile, time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks/semantic-protocol"
CONFIG = BASE / "config-v1.json"
PREREG = BASE / "preregistration-v1.json"
PERSISTENT = BASE / "persistent-instructions-v1.md"
PROMPT = BASE / "prompt-v1.md"
RESULT = ROOT / "benchmarks/results/semantic-protocol-v1/raw.jsonl"
REPRESENTATIONS = ("python-ordinary", "go-ordinary", "rust-ordinary", "tacitra-ordinary", "tacitra-semantic")

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module

MODEL = load("semantic_model_base", ROOT / "benchmarks/model_harness.py")
MODEL.STATIC.BENCHMARKS = BASE

def load_config():
    value = json.loads(CONFIG.read_text())
    required = {"schema_version","provider","model","settings","request_timeout_seconds","max_output_characters","schedule_seed","repetitions"}
    if set(value) != required or value["schema_version"] != 1 or value["provider"] != "openai-responses" or value["repetitions"] != 1:
        raise MODEL.ModelBenchmarkError("invalid semantic protocol config v1")
    return value

def heldout_cases():
    cases = [(p,c) for p,c in MODEL.STATIC.discover_cases() if c["id"].startswith("sp-heldout-")]
    if len(cases) != 60: raise MODEL.ModelBenchmarkError(f"expected 60 held-out cases, found {len(cases)}")
    return cases

def schedule(config, cases):
    rng = random.Random(config["schedule_seed"]); cases = list(cases); rng.shuffle(cases)
    result=[]
    for repetition in range(1, config["repetitions"]+1):
        for index,(path,case) in enumerate(cases):
            order=list(REPRESENTATIONS); offset=(index+repetition-1)%len(order); order=order[offset:]+order[:offset]
            if (index+repetition)%2: order.reverse()
            by_id={r["id"]:r for r in case["representations"]}
            result.extend((path,case,by_id[name],repetition) for name in order)
    return result

def schedule_document(config,cases):
    return [{"case_id":c["id"],"representation":r["id"],"repetition":n} for _,c,r,n in schedule(config,cases)]

def pins(config,cases):
    files={
      "builder_revision":BASE/"build_cases.py", "definitions_revision":BASE/"definitions-v1.json",
      "config_revision":CONFIG, "config_schema_revision":BASE/"config-v1.schema.json",
      "case_schema_revision":BASE/"case-v1.schema.json", "result_schema_revision":BASE/"result-v1.schema.json",
      "harness_revision":Path(__file__), "base_harness_revision":ROOT/"benchmarks/model_harness.py",
      "comparison_revision":ROOT/"benchmarks/semantic_protocol_compare.py",
      "report_revision":ROOT/"benchmarks/semantic_protocol_report.py",
      "persistent_instructions_revision":PERSISTENT, "prompt_revision":PROMPT,
      "protocol_profile_revision":BASE/"protocol-profile-v1.md",
      "preregistration_schema_revision":BASE/"preregistration-v1.schema.json",
      "task_capsule_schema_revision":ROOT/"protocol/schema/task-capsule-v1.schema.json",
      "typed_edit_schema_revision":ROOT/"protocol/schema/typed-edit-v1.schema.json",
      "repair_context_schema_revision":ROOT/"protocol/schema/repair-context-v1.schema.json",
      "ai_library_revision":ROOT/"crates/tacitra-agent/src/ai.rs",
    }
    result={k:MODEL.sha256(v.read_bytes()) for k,v in files.items()}
    result["case_revisions"]={c["id"]:MODEL.STATIC.case_revision(p,c) for p,c in cases}
    result["schedule_revision"]=MODEL.sha256(MODEL.canonical_json(schedule_document(config,cases)))
    return result

def validate_prereg(config,cases):
    doc=json.loads(PREREG.read_text())
    ok=(doc.get("id")=="semantic-protocol-v1" and doc.get("status")=="frozen-before-run" and
        doc.get("design",{}).get("heldout_cases")==60 and doc.get("design",{}).get("total_trials")==300 and
        doc.get("pins")==pins(config,cases))
    if not ok: raise MODEL.ModelBenchmarkError("semantic protocol preregistration does not match frozen inputs")
    return doc,MODEL.sha256(PREREG.read_bytes())

def prompt_for(path,case,representation):
    if representation["id"] != "tacitra-semantic": return MODEL.base_prompt(path,case,representation)
    directory=path.parent; template=PROMPT.read_text(); spec,sb,sh=MODEL.read_labeled(directory,representation["specification"])
    context,cb,ch=MODEL.read_labeled(directory,representation["repository_context"]); diag,db,dh=MODEL.read_labeled(directory,representation["diagnostic_context"])
    text=template.format(artifact_contract="one compact typed-edit-v1 JSON document",specification=spec or "(none)",repository_context=context,diagnostics=diag or "(none)")
    return text,{"instruction_bytes":PERSISTENT.stat().st_size,"prompt_template_bytes":len(template.encode()),"specification_bytes":sb,"repository_context_bytes":cb,"task_bytes":0,"initial_diagnostic_bytes":db,"repair_context_bytes":0,"hashes":{"prompt_template":MODEL.sha256(template.encode()),"task":"embedded-in-capsule","specification":sh,"repository_context":ch,"initial_diagnostic":dh}}

def semantic_repair(artifact,failure):
    if artifact and failure.get("phase")=="prepare":
        try:
            value=json.loads(failure.get("stdout") or "{}")
            if isinstance(value,dict) and isinstance(value.get("repair"),dict):
                return "\n\nREPAIR REQUIRED\n"+json.dumps(value["repair"],sort_keys=True,separators=(",",":"))+"\nReturn only a corrected artifact in the same JSON envelope."
        except json.JSONDecodeError: pass
    compact={"code":"A0008","op":None,"target":None,"expected":None,"actual":None,"values":[],"allowed":["body","expr"],"hash":None,"retry":True}
    return "\n\nREPAIR REQUIRED\n"+json.dumps(compact,sort_keys=True,separators=(",",":"))+"\nReturn only a corrected artifact in the same JSON envelope."

def run_trial(client,config,path,case,rep,repetition,run_id,prereg_revision,timeout):
    started=time.monotonic(); instructions=PERSISTENT.read_text(); initial,components=prompt_for(path,case,rep); repair=""; attempts=[]; final=None
    for attempt_no in range(1,case["max_repair_rounds"]+2):
        prompt=initial+repair; current=dict(components); current["repair_context_bytes"]=len(repair.encode()); request={"model":client.model,"instructions":instructions,"input":prompt,"settings":client.settings}
        attempt_started=time.monotonic(); reply=client.generate(instructions,prompt); artifact=None
        try:
            artifact=MODEL.extract_artifact(reply.text,config["max_output_characters"]); validation=MODEL.validate_artifact(path,case,rep,artifact,timeout)
        except MODEL.ModelBenchmarkError as error:
            validation={"compile_ok":False,"tests_ok":False,"accepted":False,"failure":{"phase":"model_output","message":str(error)}}
        attempts.append({"attempt":attempt_no,"request_hash":MODEL.sha256(MODEL.canonical_json(request)),"input_text":prompt,"context_bytes":current,"response_id":reply.response_id,"response_text":reply.text,"response_hash":MODEL.sha256(reply.text.encode()),"artifact":artifact,"usage":{"input_tokens":reply.input_tokens,"output_tokens":reply.output_tokens,"total_tokens":reply.total_tokens,"cached_input_tokens":reply.cached_input_tokens,"reasoning_tokens":reply.reasoning_tokens},"validation":validation,"wall_clock_time":round(time.monotonic()-attempt_started,6)})
        final=artifact
        if validation["accepted"]: break
        repair=semantic_repair(artifact,validation["failure"]) if rep["id"]=="tacitra-semantic" else MODEL.repair_context(artifact,validation["failure"])
    totals={f:sum(a["usage"][f] for a in attempts) for f in ("input_tokens","output_tokens","total_tokens","cached_input_tokens","reasoning_tokens")}; totals["repair_output_tokens"]=sum(a["usage"]["output_tokens"] for a in attempts[1:])
    accepted=attempts[-1]["validation"]["accepted"]
    row={"schema_version":3,"evidence":"measured","measurement_mode":"model","run_id":run_id,"trial_id":f"{run_id}:{case['id']}:{rep['id']}:{repetition:03d}","case_id":case["id"],"category":case["category"],"representation":rep["id"],"language":rep["language"],"surface":rep["surface"],"pins":{"suite":"semantic-protocol-v1","case_revision":MODEL.STATIC.case_revision(path,case),"harness_revision":MODEL.sha256(Path(__file__).read_bytes()),"base_harness_revision":MODEL.sha256((ROOT/"benchmarks/model_harness.py").read_bytes()),"config_revision":MODEL.sha256(MODEL.canonical_json(config)),"preregistration_revision":prereg_revision,"provider":client.provider,"endpoint":client.endpoint,"model":client.model,"model_settings":client.settings,"usage_source":"provider_response","environment":MODEL.environment_snapshot()},"persistent_instructions":{"text":instructions,"hash":MODEL.sha256(instructions.encode())},"attempts":attempts,"metrics":totals,"compile_at_1":attempts[0]["validation"]["compile_ok"],"pass_at_1":attempts[0]["validation"]["tests_ok"],"repair_rounds":len(attempts)-1,"max_repair_rounds":case["max_repair_rounds"],"patch_size":None if final is None else len(final.encode()),"accepted":accepted,"wall_clock_time":round(time.monotonic()-started,6),"failure":None if accepted else attempts[-1]["validation"]["failure"]}
    MODEL.validate_model_result(row); return row

@dataclass
class FakeClient:
    responses:list[str]; provider:str="fake-semantic"; model:str="fake-reference-v1"; endpoint:str="local://fake"; settings:dict=None
    def __post_init__(self): self.settings={} if self.settings is None else self.settings
    def generate(self,instructions,input_text):
        text=self.responses.pop(0); i=len((instructions+input_text).encode()); o=len(text.encode()); return MODEL.ModelReply(text,None,i,o,i+o,0,0)

def write_run(client,config,cases,output,run_id,revision,timeout):
    if output.exists() or output.with_suffix(output.suffix+".events.jsonl").exists(): raise MODEL.ModelBenchmarkError("refusing to overwrite result or event journal")
    output.parent.mkdir(parents=True,exist_ok=True); events=output.with_suffix(output.suffix+".events.jsonl")
    with output.open("x") as stream, events.open("x") as journal:
        journal.write(json.dumps({"event":"run_started","run_id":run_id,"trials":300,"schedule_revision":pins(config,cases)["schedule_revision"]},sort_keys=True)+"\n"); journal.flush()
        for path,case,rep,n in schedule(config,cases):
            identity={"case_id":case["id"],"representation":rep["id"],"repetition":n}; journal.write(json.dumps({"event":"trial_started",**identity},sort_keys=True)+"\n"); journal.flush()
            try: row=run_trial(client,config,path,case,rep,n,run_id,revision,timeout)
            except BaseException as error:
                journal.write(json.dumps({"event":"trial_interrupted",**identity,"error_type":type(error).__name__},sort_keys=True)+"\n"); journal.flush(); raise
            stream.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n"); stream.flush(); journal.write(json.dumps({"event":"trial_completed",**identity,"accepted":row["accepted"],"attempts":len(row["attempts"])},sort_keys=True)+"\n"); journal.flush()

def summary(rows):
    accepted=sum(r["accepted"] for r in rows); metric=MODEL.metric
    return {"trials":len(rows),"accepted":accepted,"acceptance_rate":accepted/len(rows),"compile_at_1_rate":sum(r["compile_at_1"] for r in rows)/len(rows),"pass_at_1_rate":sum(r["pass_at_1"] for r in rows)/len(rows),"total_tokens_per_accepted_solution":None if not accepted else sum(r["metrics"]["total_tokens"] for r in rows)/accepted,**{f:metric([r["metrics"][f] for r in rows]) for f in ("input_tokens","output_tokens","total_tokens","cached_input_tokens","reasoning_tokens")},"repair_rounds":metric([r["repair_rounds"] for r in rows]),"patch_size":metric([r["patch_size"] for r in rows]),"wall_clock_time":metric([r["wall_clock_time"] for r in rows])}

def aggregate(raw,output):
    rows=MODEL.read_rows(raw)
    if len(rows)!=300: raise MODEL.ModelBenchmarkError(f"expected 300 rows, found {len(rows)}")
    doc={"schema_version":1,"evidence":"measured","trials":300,"representations":[{"representation":name,**summary([r for r in rows if r["representation"]==name])} for name in REPRESENTATIONS],"categories":[{"category":cat,"representation":name,**summary([r for r in rows if r["category"]==cat and r["representation"]==name])} for cat in sorted({r["category"] for r in rows}) for name in REPRESENTATIONS]}
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n")

def main():
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("validate"); sub.add_parser("dry-run"); run=sub.add_parser("run"); run.add_argument("--env-file",type=Path); run.add_argument("--output",type=Path,default=RESULT); run.add_argument("--command-timeout",type=int,default=30)
    agg=sub.add_parser("aggregate"); agg.add_argument("--raw",type=Path,required=True); agg.add_argument("--output",type=Path,required=True); args=parser.parse_args()
    try:
        if args.command=="aggregate": aggregate(args.raw,args.output); return 0
        config=load_config(); cases=heldout_cases(); _,revision=validate_prereg(config,cases)
        if args.command=="validate": print(json.dumps({"valid":True,"cases":60,"trials":300,"preregistration_revision":revision})); return 0
        if args.command=="dry-run":
            responses=[json.dumps({"artifact":MODEL.STATIC.relative_file(p.parent,r["artifact"]).read_text()},separators=(",",":")) for p,c,r,n in schedule(config,cases)]
            with tempfile.TemporaryDirectory() as d:
                out=Path(d)/"raw.jsonl"; write_run(FakeClient(responses),config,cases,out,"semantic-protocol-v1-dry-run",revision,30); rows=MODEL.read_rows(out)
                if len(rows)!=300 or not all(r["accepted"] for r in rows): raise MODEL.ModelBenchmarkError("fake-model dry-run failed")
            print(json.dumps({"valid":True,"fake_trials":300,"accepted":300})); return 0
        key=MODEL.load_api_key(args.env_file)
        if not key: raise MODEL.ModelBenchmarkError("OPENAI_API_KEY is required and is never stored")
        write_run(MODEL.OpenAIResponsesClient(config,key),config,cases,args.output,"semantic-protocol-v1",revision,args.command_timeout)
    except (MODEL.ModelBenchmarkError,MODEL.STATIC.BenchmarkError,OSError,RuntimeError) as error:
        print(f"semantic-protocol error: {error}",file=sys.stderr); return 2
    return 0

if __name__=="__main__": raise SystemExit(main())
