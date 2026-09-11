use std::{fs, process::Command};

const AGENT_SOURCE: &str = include_str!("../../../examples/agent_target.taci");

fn tacitra() -> Command {
    Command::new(env!("CARGO_BIN_EXE_tacitra"))
}

fn fixture(name: &str, source: &str) -> std::path::PathBuf {
    let path = std::env::temp_dir().join(format!("tacitra-{name}-{}.taci", std::process::id()));
    fs::write(&path, source).expect("fixture should be writable");
    path
}

#[test]
fn parse_json_emits_source_positioned_ast() {
    let path = fixture("parse", "let answer = 42;");
    let output = tacitra()
        .args(["parse", "--json", path.to_str().unwrap()])
        .output()
        .unwrap();
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(stdout.contains("\"kind\":\"program\""));
    assert!(stdout.contains("\"byte\":0,\"line\":1,\"column\":1"));
    assert!(stdout.contains("\"kind\":\"integer\""));
    assert!(stdout.contains("\"value\":42"));
}

#[test]
fn check_json_is_nonzero_and_structured_for_invalid_source() {
    let path = fixture("check", "let answer = ;");
    let output = tacitra()
        .args(["check", "--json", path.to_str().unwrap()])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(1));
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(stdout
        .starts_with("{\"schema_version\":1,\"valid\":false,\"diagnostics\":[{\"code\":\"P0015\""));
}

#[test]
fn format_check_distinguishes_noncanonical_source() {
    let path = fixture("format", "let answer=40+2;");
    let before = tacitra()
        .args(["fmt", "--check", path.to_str().unwrap()])
        .status()
        .unwrap();
    assert_eq!(before.code(), Some(1));
    assert!(tacitra()
        .args(["fmt", "--write", path.to_str().unwrap()])
        .status()
        .unwrap()
        .success());
    assert_eq!(fs::read_to_string(path).unwrap(), "let answer = 40 + 2;\n");
}

#[test]
fn check_reports_typed_json_diagnostics() {
    let path = fixture("typed-check", "fn main() -> Int { false }");
    let output = tacitra()
        .args(["check", "--json", path.to_str().unwrap()])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(1));
    let stdout = String::from_utf8(output.stdout).unwrap();
    let document: serde_json::Value = serde_json::from_str(&stdout).unwrap();
    assert_eq!(document["schema_version"], 1);
    assert!(stdout.contains("\"code\":\"T0001\""));
    assert!(stdout.contains("\"expected_type\":\"Int\""));
    assert!(stdout.contains("\"actual_type\":\"Bool\""));
}

#[test]
fn run_executes_checked_main() {
    let path = format!(
        "{}/../../examples/algebraic.taci",
        env!("CARGO_MANIFEST_DIR")
    );
    let output = tacitra().args(["run", "--json", &path]).output().unwrap();
    assert!(output.status.success());
    assert_eq!(
        String::from_utf8(output.stdout).unwrap(),
        "{\"type\":\"String\",\"value\":\"Ada\"}\n"
    );
}

#[test]
fn semantic_query_returns_bounded_deterministic_json() {
    let path = fixture("query", AGENT_SOURCE);
    let first = tacitra()
        .args(["symbol.describe", path.to_str().unwrap(), "increment"])
        .output()
        .unwrap();
    let second = tacitra()
        .args([
            "symbol.describe",
            path.to_str().unwrap(),
            "sym:fn:increment",
        ])
        .output()
        .unwrap();
    assert!(first.status.success());
    assert_eq!(first.stdout, second.stdout);
    let json: serde_json::Value = serde_json::from_slice(&first.stdout).unwrap();
    assert_eq!(json["detail"]["return_type"], "Int");
    assert!(!String::from_utf8(first.stdout)
        .unwrap()
        .contains("value + 1"));
}

#[test]
fn patch_validate_is_dry_run_and_patch_apply_writes_checked_source() {
    let path = fixture("patch-target", AGENT_SOURCE);
    let summary = tacitra()
        .args(["module.summary", path.to_str().unwrap()])
        .output()
        .unwrap();
    let summary: serde_json::Value = serde_json::from_slice(&summary.stdout).unwrap();
    let document = serde_json::json!({
        "schema_version": 1,
        "base_hash": summary["content_hash"],
        "operations": [{
            "op": "replace_function_body",
            "target": "sym:fn:increment",
            "replacement": "{ value + 2 }"
        }]
    });
    let patch_path = fixture("patch-document", &document.to_string());
    let before = fs::read_to_string(&path).unwrap();
    let validation = tacitra()
        .args([
            "patch.validate",
            path.to_str().unwrap(),
            patch_path.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(validation.status.success());
    assert_eq!(fs::read_to_string(&path).unwrap(), before);
    let validation: serde_json::Value = serde_json::from_slice(&validation.stdout).unwrap();
    assert_eq!(validation["valid"], true);
    assert!(validation["diff"].as_str().unwrap().contains("value + 2"));

    let application = tacitra()
        .args([
            "patch.apply",
            path.to_str().unwrap(),
            patch_path.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(application.status.success());
    assert_ne!(fs::read_to_string(&path).unwrap(), before);
    let execution = tacitra()
        .args(["run", path.to_str().unwrap()])
        .output()
        .unwrap();
    assert!(execution.status.success());
    assert_eq!(String::from_utf8(execution.stdout).unwrap(), "43\n");
}

#[test]
fn interop_inspection_call_and_external_error_are_structured() {
    let manifest = format!(
        "{}/../../examples/interop/python/manifest.json",
        env!("CARGO_MANIFEST_DIR")
    );
    let arguments = fixture("interop-arguments", r#"{"left":20,"right":22}"#);
    let inspection = tacitra()
        .args(["interop.inspect", &manifest])
        .output()
        .unwrap();
    assert!(inspection.status.success());
    let summary: serde_json::Value = serde_json::from_slice(&inspection.stdout).unwrap();
    assert_eq!(summary["module"], "python_math");
    assert!(summary.get("command").is_none());

    let call = tacitra()
        .args([
            "interop.call",
            &manifest,
            "add",
            arguments.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(call.status.success());
    let outcome: serde_json::Value = serde_json::from_slice(&call.stdout).unwrap();
    assert_eq!(outcome["result"], 42);

    let empty = fixture("interop-empty", "{}");
    let failure = tacitra()
        .args([
            "interop.call",
            &manifest,
            "explode",
            empty.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert_eq!(failure.status.code(), Some(1));
    let error: serde_json::Value = serde_json::from_slice(&failure.stdout).unwrap();
    assert_eq!(error["schema_version"], 1);
    assert_eq!(error["error"]["code"], "I0011");
}

#[test]
fn compact_agent_context_commands_are_available() {
    let source = fixture("edit-context", AGENT_SOURCE);
    let edit = tacitra()
        .args(["symbol.edit-context", source.to_str().unwrap(), "increment"])
        .output()
        .unwrap();
    assert!(edit.status.success());
    let edit: serde_json::Value = serde_json::from_slice(&edit.stdout).unwrap();
    assert_eq!(edit["body_target"], "sym:fn:increment");

    let manifest = format!(
        "{}/../../examples/interop/python/manifest.json",
        env!("CARGO_MANIFEST_DIR")
    );
    let external = tacitra()
        .args(["external.call-context", &manifest, "add"])
        .output()
        .unwrap();
    assert!(external.status.success());
    let external: serde_json::Value = serde_json::from_slice(&external.stdout).unwrap();
    assert_eq!(external["name"], "add");
    assert!(external.get("transport").is_none());
}

#[test]
fn help_and_version_are_successful_and_document_commands() {
    let help = tacitra().arg("--help").output().unwrap();
    assert!(help.status.success());
    assert!(help.stderr.is_empty());
    let text = String::from_utf8(help.stdout).unwrap();
    for command in [
        "parse",
        "fmt",
        "check",
        "run",
        "patch.validate",
        "interop.call",
    ] {
        assert!(text.contains(command), "help omitted {command}");
    }

    let version = tacitra().arg("--version").output().unwrap();
    assert!(version.status.success());
    assert_eq!(
        String::from_utf8(version.stdout).unwrap(),
        "tacitra 0.1.0 (experimental)\n"
    );
}

#[test]
fn public_error_schemas_have_unique_versioned_ids() {
    let schemas = [
        include_str!("../../../protocol/schema/diagnostics-v1.schema.json"),
        include_str!("../../../protocol/schema/agent-error-v1.schema.json"),
        include_str!("../../../protocol/schema/interop-error-v1.schema.json"),
        include_str!("../../../protocol/schema/patch.schema.json"),
        include_str!("../../../protocol/schema/interop-manifest.schema.json"),
    ];
    let mut identifiers = std::collections::BTreeSet::new();
    for schema in schemas {
        let value: serde_json::Value = serde_json::from_str(schema).unwrap();
        let identifier = value["$id"].as_str().unwrap().to_owned();
        assert!(
            identifier.contains("v1"),
            "unversioned schema ID: {identifier}"
        );
        assert!(identifiers.insert(identifier));
    }
}
