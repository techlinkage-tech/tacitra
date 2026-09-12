import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
RUN=load("semantic_protocol_test_runner",ROOT/"benchmarks/semantic_protocol.py")
class SemanticProtocolTest(unittest.TestCase):
    def test_heldout_is_new_and_has_no_reference_leakage(self):
        cases=RUN.heldout_cases();self.assertEqual(len(cases),60)
        old=set()
        for p in (ROOT/"benchmarks/cross-language/cases").glob("*/task.md"):old.add(p.read_text().strip())
        for path,case in cases:
            task=(path.parent/case["prompt"]).read_text().strip();self.assertNotIn(task,old)
            prompt,_=RUN.prompt_for(path,case,next(r for r in case["representations"] if r["id"]=="tacitra-semantic"))
            self.assertNotIn("reference.",prompt);self.assertNotIn("unrelated_alpha",prompt);self.assertEqual(prompt.count(task),1)
    def test_schedule_is_deterministic_interleaved_and_complete(self):
        config=RUN.load_config();cases=RUN.heldout_cases();a=RUN.schedule_document(config,cases);b=RUN.schedule_document(config,cases)
        self.assertEqual(a,b);self.assertEqual(len(a),300);self.assertEqual(len({(x["case_id"],x["representation"]) for x in a}),300)
    def test_fake_model_all_paths(self):
        config=RUN.load_config();cases=RUN.heldout_cases();scheduled=RUN.schedule(config,cases)
        responses=[json.dumps({"artifact":RUN.MODEL.STATIC.relative_file(p.parent,r["artifact"]).read_text()},separators=(",",":")) for p,c,r,n in scheduled]
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/"raw.jsonl";RUN.write_run(RUN.FakeClient(responses),config,cases,output,"test","unfrozen-test",30);rows=RUN.MODEL.read_rows(output)
            self.assertEqual(len(rows),300);self.assertTrue(all(r["accepted"] for r in rows))
    def test_semantic_repair_is_bounded_and_source_free(self):
        failure={"phase":"prepare","stdout":json.dumps({"repair":{"code":"A0005","op":0,"target":"sym:fn:x","expected":"Int","actual":"Bool","values":[],"allowed":["body"],"hash":"sha256:x","retry":True}}),"stderr":"full source forbidden"}
        value=RUN.semantic_repair("{}",failure);self.assertIn("A0005",value);self.assertNotIn("full source forbidden",value);self.assertNotIn("Previous artifact",value)
if __name__=="__main__":unittest.main()
