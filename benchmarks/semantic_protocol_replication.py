#!/usr/bin/env python3
"""Future full replication runner; real execution requires a new frozen preregistration."""

from __future__ import annotations
import argparse, importlib.util, json, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"benchmarks/semantic-protocol-replication-v1"
PREREG=BASE/"preregistration-v1.json"
RESULT=ROOT/"benchmarks/results/semantic-protocol-replication-v1/raw.jsonl"
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
RECOVERY=load("semantic_replication_recovery",ROOT/"benchmarks/semantic_protocol_recovery.py");FROZEN=RECOVERY.FROZEN;MODEL=FROZEN.MODEL

class ProviderFailure(Exception):pass

def replication_pins():
    paths={"runner_revision":Path(__file__),"runtime_revision":ROOT/"benchmarks/runtime_environment.py","recovery_revision":ROOT/"benchmarks/semantic_protocol_recovery.py","aggregate_revision":ROOT/"benchmarks/semantic_protocol_aggregate_v2.py","comparison_revision":ROOT/"benchmarks/semantic_protocol_compare_v2.py","inherited_preregistration_revision":ROOT/"benchmarks/semantic-protocol/preregistration-v1.json"}
    return {name:MODEL.sha256(path.read_bytes()) for name,path in paths.items()}

def validate_replication_preregistration():
    if not PREREG.is_file():raise RECOVERY.RUNTIME.EnvironmentFailure("environment_preflight_failure",None,"new replication preregistration is not frozen")
    document=json.loads(PREREG.read_text())
    if document.get("status")!="frozen-before-run" or document.get("pins")!=replication_pins() or document.get("design",{}).get("total_trials")!=300:
        raise RECOVERY.RUNTIME.EnvironmentFailure("environment_preflight_failure",None,"new replication preregistration does not match the harness")
    return document,MODEL.sha256(PREREG.read_bytes())

def validate_text(runtime,path,case,representation,artifact,timeout):
    with tempfile.TemporaryDirectory(prefix="tacitra-replication-artifact-") as directory:
        candidate=Path(directory)/Path(representation["artifact"]).name;candidate.write_text(artifact,encoding="utf-8")
        return RECOVERY.validate_artifact(runtime,path,case,representation,candidate,timeout)

def run_trial(runtime,client,config,path,case,representation,repetition,run_id,revision,timeout):
    started=time.monotonic();instructions=FROZEN.PERSISTENT.read_text();initial,components=FROZEN.prompt_for(path,case,representation);repair="";attempts=[];final=None
    for attempt_no in range(1,case["max_repair_rounds"]+2):
        prompt=initial+repair;request={"model":client.model,"instructions":instructions,"input":prompt,"settings":client.settings};attempt_started=time.monotonic()
        try:reply=client.generate(instructions,prompt)
        except Exception as error:
            # Provider exceptions can contain request headers or credentials. Keep
            # the failure class for diagnosis without persisting exception text.
            raise ProviderFailure(type(error).__name__) from error
        artifact=None
        try:
            artifact=MODEL.extract_artifact(reply.text,config["max_output_characters"]);validation=validate_text(runtime,path,case,representation,artifact,timeout)
        except MODEL.ModelBenchmarkError as error:
            validation={"accepted":False,"compile_ok":False,"tests_ok":False,"failure_classification":"model_generation_failure","phase":"model_output","exit_code":None,"timed_out":False,"stdout":"","stderr":str(error)}
        failure=None if validation["accepted"] else {"phase":validation["phase"],"exit_code":validation["exit_code"],"stdout":validation["stdout"],"stderr":validation["stderr"],"classification":validation["failure_classification"]}
        attempts.append({"attempt":attempt_no,"request_hash":MODEL.sha256(MODEL.canonical_json(request)),"input_text":prompt,"context_bytes":{**components,"repair_context_bytes":len(repair.encode())},"response_id":reply.response_id,"response_text":reply.text,"response_hash":MODEL.sha256(reply.text.encode()),"artifact":artifact,"usage":{"input_tokens":reply.input_tokens,"output_tokens":reply.output_tokens,"total_tokens":reply.total_tokens,"cached_input_tokens":reply.cached_input_tokens,"reasoning_tokens":reply.reasoning_tokens},"validation":{"compile_ok":validation["compile_ok"],"tests_ok":validation["tests_ok"],"accepted":validation["accepted"],"failure":failure},"wall_clock_time":round(time.monotonic()-attempt_started,6)})
        final=artifact
        if validation["accepted"]:break
        repair=FROZEN.semantic_repair(artifact,failure) if representation["id"]=="tacitra-semantic" else MODEL.repair_context(artifact,failure)
    accepted=attempts[-1]["validation"]["accepted"];totals={field:sum(a["usage"][field] for a in attempts) for field in ("input_tokens","output_tokens","total_tokens","cached_input_tokens","reasoning_tokens")};totals["repair_output_tokens"]=sum(a["usage"]["output_tokens"] for a in attempts[1:])
    row={"schema_version":3,"evidence":"measured","measurement_mode":"model","run_id":run_id,"trial_id":f"{run_id}:{case['id']}:{representation['id']}:{repetition:03d}","case_id":case["id"],"category":case["category"],"representation":representation["id"],"language":representation["language"],"surface":representation["surface"],"pins":{"suite":"semantic-protocol-replication-v1","case_revision":MODEL.STATIC.case_revision(path,case),"harness_revision":MODEL.sha256(Path(__file__).read_bytes()),"config_revision":MODEL.sha256(MODEL.canonical_json(config)),"preregistration_revision":revision,"provider":client.provider,"endpoint":client.endpoint,"model":client.model,"model_settings":client.settings,"usage_source":"provider_response","environment":runtime.public_record()},"persistent_instructions":{"text":instructions,"hash":MODEL.sha256(instructions.encode())},"attempts":attempts,"metrics":totals,"compile_at_1":attempts[0]["validation"]["compile_ok"],"pass_at_1":attempts[0]["validation"]["tests_ok"],"repair_rounds":len(attempts)-1,"max_repair_rounds":case["max_repair_rounds"],"patch_size":None if final is None else len(final.encode()),"accepted":accepted,"wall_clock_time":round(time.monotonic()-started,6),"failure":None if accepted else attempts[-1]["validation"]["failure"]};MODEL.validate_model_result(row);return row

def write_run(runtime,client,config,cases,output,revision,timeout):
    events=output.with_suffix(output.suffix+".events.jsonl")
    if output.exists() or events.exists():raise RECOVERY.RUNTIME.EnvironmentFailure("environment_preflight_failure",None,"replication output is already in use")
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("x") as stream,events.open("x") as journal:
        journal.write(json.dumps({"event":"run_started","run_id":"semantic-protocol-replication-v1","trials":300},sort_keys=True)+"\n");journal.flush()
        for path,case,representation,repetition in FROZEN.schedule(config,cases):
            identity={"case_id":case["id"],"representation":representation["id"],"repetition":repetition};journal.write(json.dumps({"event":"trial_started",**identity},sort_keys=True)+"\n");journal.flush()
            try:row=run_trial(runtime,client,config,path,case,representation,repetition,"semantic-protocol-replication-v1",revision,timeout)
            except ProviderFailure:
                journal.write(json.dumps({"event":"run_aborted",**identity,"classification":"provider_failure"},sort_keys=True)+"\n");journal.flush();raise
            stream.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n");stream.flush();journal.write(json.dumps({"event":"trial_completed",**identity,"accepted":row["accepted"]},sort_keys=True)+"\n");journal.flush()

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest="command",required=True);sub.add_parser("preflight");run=sub.add_parser("run");run.add_argument("--env-file",type=Path);run.add_argument("--output",type=Path,default=RESULT);run.add_argument("--command-timeout",type=int,default=30);args=parser.parse_args()
    try:
        output=RESULT if args.command=="preflight" else args.output
        runtime,config,cases,_=RECOVERY.run_preflight(output=output)
        if args.command=="preflight":print(json.dumps(runtime.public_record(),indent=2,sort_keys=True));return 0
        _,revision=validate_replication_preregistration()
        key=MODEL.load_api_key(args.env_file)
        if not key:raise RECOVERY.RUNTIME.EnvironmentFailure("environment_preflight_failure",None,"OPENAI_API_KEY is required")
        client=MODEL.OpenAIResponsesClient(config,key)
        write_run(runtime,client,config,cases,args.output,revision,args.command_timeout)
    except (RECOVERY.RUNTIME.EnvironmentFailure,ProviderFailure,MODEL.ModelBenchmarkError,OSError) as error:
        classification=error.classification if isinstance(error,RECOVERY.RUNTIME.EnvironmentFailure) else "provider_failure" if isinstance(error,ProviderFailure) else "environment_preflight_failure"
        print(json.dumps({"classification":classification,"reason":str(error)},sort_keys=True),file=sys.stderr);return 2
    return 0
if __name__=="__main__":raise SystemExit(main())
