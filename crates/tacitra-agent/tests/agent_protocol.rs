use serde_json::Value;
use std::panic::{catch_unwind, AssertUnwindSafe};
use tacitra_agent::{
    apply_patch, module_summary, parse_patch, symbol_describe, symbol_edit_context,
    symbol_references, type_describe, validate_patch, SemanticModule,
};
use tacitra_semantics::{execute_main, Value as RuntimeValue};

const SOURCE: &str = include_str!("../../../examples/agent_target.taci");
const PATCH: &str = include_str!("../../../examples/patches/increment-by-two.json");

fn module(source: &str) -> SemanticModule {
    SemanticModule::build(source).expect("source should check")
}

#[test]
fn semantic_ids_and_hash_ignore_formatting_and_comments() {
    let canonical = module("fn add(value: Int) -> Int {\n  value + 1\n}\n");
    let trivia = module("// heading\nfn add( value:Int)->Int { // body\n value+1 // result\n}\n");
    assert_eq!(canonical.semantic_ids(), trivia.semantic_ids());
    assert_eq!(canonical.content_hash(), trivia.content_hash());
}

#[test]
fn symbol_ids_survive_small_body_changes() {
    let first = module("fn add(value: Int) -> Int { value + 1 }");
    let second = module("fn add(value: Int) -> Int { value + 2 }");
    assert_eq!(first.semantic_ids(), second.semantic_ids());
    assert_ne!(first.content_hash(), second.content_hash());
}

#[test]
fn queries_are_deterministic_and_do_not_return_source() {
    let module = module(SOURCE);
    assert_eq!(module_summary(&module), module_summary(&module));
    let description = symbol_describe(&module, "increment").unwrap();
    assert_eq!(
        description,
        symbol_describe(&module, "sym:fn:increment").unwrap()
    );
    assert!(!description.contains("value + 1"));
    let json: Value = serde_json::from_str(&description).unwrap();
    assert_eq!(json["detail"]["return_type"], "Int");
    assert_eq!(json["detail"]["failure_type"], Value::Null);
    assert_eq!(json["detail"]["effects"], serde_json::json!([]));
    assert_eq!(json["detail"]["contracts"], serde_json::json!([]));
    assert!(json["expressions"]
        .as_array()
        .unwrap()
        .iter()
        .any(|value| value["id"] == "expr:sym:fn:increment/body/result"));
}

#[test]
fn edit_context_is_smaller_stable_and_keeps_patch_targets() {
    let canonical = module("fn add(value: Int) -> Int { value + 1 }");
    let trivia = module("// comment\nfn add( value:Int)->Int { value+1 }");
    let context = symbol_edit_context(&canonical, "add").unwrap();
    assert_eq!(context, symbol_edit_context(&trivia, "add").unwrap());
    assert!(context.len() < symbol_describe(&canonical, "add").unwrap().len());
    let value: Value = serde_json::from_str(&context).unwrap();
    assert_eq!(value["body_target"], "sym:fn:add");
    assert!(value["leaves"]
        .as_array()
        .unwrap()
        .iter()
        .any(|leaf| { leaf["id"] == "expr:sym:fn:add/body/result/right" && leaf["value"] == 1 }));
    assert!(value.get("span").is_none());
}

#[test]
fn reference_type_and_call_queries_are_resolved() {
    let module = module(SOURCE);
    let references: Value =
        serde_json::from_str(&symbol_references(&module, "increment").unwrap()).unwrap();
    assert_eq!(references["references"].as_array().unwrap().len(), 1);
    assert_eq!(references["references"][0]["kind"], "call");
    let ty: Value = serde_json::from_str(&type_describe(&module, "Config").unwrap()).unwrap();
    assert_eq!(ty["kind"], "record");
    assert_eq!(ty["detail"]["fields"].as_array().unwrap().len(), 2);
    let summary: Value = serde_json::from_str(&module_summary(&module)).unwrap();
    assert!(summary["call_graph"]
        .as_array()
        .unwrap()
        .iter()
        .any(|edge| edge["callee"] == "sym:fn:increment"));
}

#[test]
fn patch_schema_and_example_are_valid_and_compact() {
    let patch = parse_patch(PATCH).unwrap();
    assert_eq!(patch.schema_version, 1);
    assert!(PATCH.len() < SOURCE.len());
    let schema: Value =
        serde_json::from_str(include_str!("../../../protocol/schema/patch.schema.json")).unwrap();
    assert_eq!(schema["properties"]["schema_version"]["const"], 1);
    assert_eq!(
        parse_patch(r#"{"schema_version":1,"base_hash":"x","operations":[],"extra":true}"#)
            .unwrap_err()
            .code,
        "A0006"
    );
    assert_eq!(
        parse_patch(r#"{"schema_version":1,"base_hash":"x","operations":[{"op":"replace_expression","target":"x","replacement":"1"}]}"#)
            .unwrap_err()
            .code,
        "A0006"
    );
    assert_eq!(
        parse_patch(r#"{"schema_version":1,"base_hash":"sha256:not-a-digest","operations":[]}"#,)
            .unwrap_err()
            .code,
        "A0006"
    );
}

#[test]
fn dry_run_does_not_change_input_and_returns_reviewable_diff() {
    let module = module(SOURCE);
    let before = SOURCE.to_owned();
    let outcome = validate_patch(&module, &parse_patch(PATCH).unwrap()).unwrap();
    assert_eq!(SOURCE, before);
    assert!(outcome.changed);
    assert!(outcome
        .diff
        .starts_with("--- a/module.taci\n+++ b/module.taci\n@@"));
    assert!(outcome.diff.contains("-  value + 1\n+  value + 2"));
    assert_eq!(
        outcome.descriptions,
        ["replace body of function `increment`"]
    );
}

#[test]
fn patch_round_trip_produces_checked_executable_source() {
    let original = module(SOURCE);
    let outcome = apply_patch(&original, &parse_patch(PATCH).unwrap()).unwrap();
    let updated = module(&outcome.updated_source);
    let parsed = tacitra_syntax::parse(&outcome.updated_source);
    assert!(parsed.diagnostics.is_empty());
    assert_eq!(
        tacitra_syntax::format_program(&parsed.program),
        outcome.updated_source
    );
    let analysis = tacitra_semantics::analyze(&parsed.program);
    assert!(analysis.diagnostics.is_empty());
    assert_eq!(
        execute_main(&analysis.program.unwrap()).unwrap(),
        RuntimeValue::Int(43)
    );
    assert_eq!(updated.content_hash(), outcome.result_hash);
}

#[test]
fn expression_patch_uses_a_semantic_path() {
    let module = module(SOURCE);
    let document = format!(
        r#"{{"schema_version":1,"base_hash":"{}","operations":[{{"op":"replace_expression","target":"expr:sym:fn:increment/body/result/right","replacement":"2"}}]}}"#,
        module.content_hash()
    );
    assert!(document.len() < SOURCE.len());
    let outcome = apply_patch(&module, &parse_patch(&document).unwrap()).unwrap();
    assert!(outcome.diff.contains("value + 2"));
}

#[test]
fn stale_missing_ambiguous_overlapping_and_invalid_patches_are_rejected() {
    let indexed = module(SOURCE);
    let stale = PATCH.replace(
        indexed.content_hash(),
        "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    );
    assert_eq!(
        validate_patch(&indexed, &parse_patch(&stale).unwrap())
            .unwrap_err()
            .code,
        "A0003"
    );
    let missing = PATCH.replace("sym:fn:increment", "sym:fn:missing");
    assert_eq!(
        validate_patch(&indexed, &parse_patch(&missing).unwrap())
            .unwrap_err()
            .code,
        "A0001"
    );
    let invalid = PATCH.replace("{ value + 2 }", "{ false }");
    assert_eq!(
        validate_patch(&indexed, &parse_patch(&invalid).unwrap())
            .unwrap_err()
            .code,
        "A0005"
    );
    let overlap = format!(
        r#"{{"schema_version":1,"base_hash":"{}","operations":[{{"op":"replace_function_body","target":"sym:fn:increment","replacement":"{{ value + 2 }}"}},{{"op":"replace_expression","target":"expr:sym:fn:increment/body/result","replacement":"value + 3"}}]}}"#,
        indexed.content_hash()
    );
    assert_eq!(
        validate_patch(&indexed, &parse_patch(&overlap).unwrap())
            .unwrap_err()
            .code,
        "A0004"
    );

    let ambiguous_source = "record Same { value: Int, } fn Same() -> Int { 1 }";
    let ambiguous_module = module(ambiguous_source);
    let ambiguous = format!(
        r#"{{"schema_version":1,"base_hash":"{}","operations":[{{"op":"replace_function_body","target":"Same","replacement":"{{ 2 }}"}}]}}"#,
        ambiguous_module.content_hash()
    );
    assert_eq!(
        validate_patch(&ambiguous_module, &parse_patch(&ambiguous).unwrap())
            .unwrap_err()
            .code,
        "A0002"
    );
}

#[test]
fn generated_patch_round_trips_are_checked_and_deterministic() {
    for value in 0..256 {
        let indexed = module(SOURCE);
        let source = format!(
            r#"{{"schema_version":1,"base_hash":"{}","operations":[{{"op":"replace_function_body","target":"sym:fn:increment","replacement":"{{ value + {value} }}"}}]}}"#,
            indexed.content_hash()
        );
        let document = parse_patch(&source).unwrap();
        let first = validate_patch(&indexed, &document).unwrap();
        let second = apply_patch(&indexed, &document).unwrap();
        assert_eq!(first, second);
        assert!(SemanticModule::build(&first.updated_source).is_ok());
        assert_eq!(
            tacitra_syntax::format_source(&first.updated_source).unwrap(),
            first.updated_source
        );
    }
}

#[test]
fn arbitrary_patch_json_and_replacements_never_panic() {
    for seed in 0..1_024_u64 {
        let mut state = seed;
        let mut data = String::new();
        for _ in 0..usize::try_from(seed % 160).unwrap() {
            state = state.wrapping_mul(1_664_525).wrapping_add(1_013_904_223);
            data.push(char::from_u32(32 + (state % 95) as u32).unwrap());
        }
        assert!(catch_unwind(AssertUnwindSafe(|| parse_patch(&data))).is_ok());

        let indexed = module(SOURCE);
        let encoded = serde_json::json!({
            "schema_version": 1,
            "base_hash": indexed.content_hash(),
            "operations": [{
                "op": "replace_function_body",
                "target": "sym:fn:increment",
                "replacement": data,
            }]
        })
        .to_string();
        let document = parse_patch(&encoded).unwrap();
        assert!(catch_unwind(AssertUnwindSafe(|| validate_patch(&indexed, &document))).is_ok());
    }
}
