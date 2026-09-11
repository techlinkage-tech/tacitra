use serde_json::json;
use std::{
    fs,
    path::{Path, PathBuf},
    process::Command,
    time::{Duration, Instant},
};
use tacitra_interop::{
    call_context, decode_bytes, encode_bytes, export_describe, invoke, manifest_summary,
    parse_manifest, validate_value, ExternalType, InvocationPolicy, Manifest,
};

fn example(language: &str, name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../examples/interop")
        .join(language)
        .join(name)
}

fn load(language: &str) -> Manifest {
    parse_manifest(&fs::read_to_string(example(language, "manifest.json")).unwrap()).unwrap()
}

fn policy(manifest: &Manifest) -> InvocationPolicy {
    InvocationPolicy::from_manifest(manifest)
}

#[test]
fn manifests_are_shared_deterministic_and_source_free() {
    for language in ["python", "go", "rust"] {
        let manifest = load(language);
        let first = manifest_summary(&manifest);
        assert_eq!(first, manifest_summary(&manifest));
        assert!(!first.contains("worker.py"));
        assert!(!first.contains("worker.go"));
        assert!(!first.contains("worker.rs"));
        let description = export_describe(&manifest, "add").unwrap();
        assert!(description.contains("\"bits\":64"));
        assert!(description.contains("add two integers"));
    }
}

#[test]
fn call_context_is_bounded_and_preserves_the_execution_contract() {
    let manifest = load("python");
    let context = call_context(&manifest, "add").unwrap();
    assert_eq!(context, call_context(&manifest, "add").unwrap());
    assert!(
        context.len()
            < fs::read_to_string(example("python", "manifest.json"))
                .unwrap()
                .len()
    );
    let value: serde_json::Value = serde_json::from_str(&context).unwrap();
    assert_eq!(value["name"], "add");
    assert_eq!(value["parameters"].as_array().unwrap().len(), 2);
    assert_eq!(value["example"]["result"], 42);
    assert!(value.get("transport").is_none());
}

#[test]
fn rejects_invalid_manifests() {
    let schema: serde_json::Value = serde_json::from_str(
        &fs::read_to_string(
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("../../protocol/schema/interop-manifest.schema.json"),
        )
        .unwrap(),
    )
    .unwrap();
    assert_eq!(schema["properties"]["schema_version"]["const"], 1);
    let source = fs::read_to_string(example("go", "manifest.json")).unwrap();
    assert_eq!(
        parse_manifest(&source.replace("\"schema_version\": 1", "\"schema_version\": 2"))
            .unwrap_err()
            .code,
        "I0002"
    );
    assert_eq!(
        parse_manifest(&source.replace("\"bits\": 64", "\"bits\": 7"))
            .unwrap_err()
            .code,
        "I0001"
    );
    assert_eq!(
        parse_manifest(&source.replace(
            "\"schema_version\": 1,",
            "\"schema_version\": 1, \"unknown\": true,",
        ))
        .unwrap_err()
        .code,
        "I0001"
    );
}

#[test]
fn common_values_round_trip_and_enforce_ranges() {
    let cases = vec![
        (ExternalType::Bool, json!(true)),
        (
            ExternalType::Int {
                signed: true,
                bits: 8,
            },
            json!(-128),
        ),
        (ExternalType::Float { bits: 64 }, json!(1.5)),
        (ExternalType::String, json!("hello")),
        (
            ExternalType::Bytes,
            json!({"$bytes": encode_bytes(b"Tacitra")}),
        ),
        (
            ExternalType::List {
                element: Box::new(ExternalType::Bool),
            },
            json!([true, false]),
        ),
        (
            ExternalType::Record {
                name: "Point".to_owned(),
                fields: vec![
                    tacitra_interop::ManifestField {
                        name: "x".to_owned(),
                        ty: ExternalType::Int {
                            signed: true,
                            bits: 32,
                        },
                    },
                    tacitra_interop::ManifestField {
                        name: "label".to_owned(),
                        ty: ExternalType::String,
                    },
                ],
            },
            json!({"x": 1, "label": "origin"}),
        ),
        (
            ExternalType::Option {
                value: Box::new(ExternalType::String),
            },
            json!({"$some": "value"}),
        ),
        (
            ExternalType::Result {
                ok: Box::new(ExternalType::String),
                error: Box::new(ExternalType::String),
            },
            json!({"$err": "failure"}),
        ),
        (
            ExternalType::Opaque {
                name: "Session".to_owned(),
            },
            json!({"$handle": {"type": "Session", "id": "worker-1"}}),
        ),
    ];
    for (ty, value) in cases {
        validate_value(&ty, &value, "value").unwrap();
        let encoded = serde_json::to_string(&value).unwrap();
        let decoded = serde_json::from_str(&encoded).unwrap();
        validate_value(&ty, &decoded, "value").unwrap();
    }
    assert_eq!(
        decode_bytes(&encode_bytes(b"\0\xffbytes")).unwrap(),
        b"\0\xffbytes"
    );
    assert_eq!(
        validate_value(
            &ExternalType::Int {
                signed: true,
                bits: 8
            },
            &json!(128),
            "value"
        )
        .unwrap_err()
        .code,
        "I0003"
    );
    assert_eq!(
        validate_value(&ExternalType::Float { bits: 32 }, &json!(1.0e100), "value")
            .unwrap_err()
            .code,
        "I0003"
    );
}

#[test]
fn python_success_exception_timeout_and_cleanup() {
    let manifest = load("python");
    let directory = example("python", "manifest.json")
        .parent()
        .unwrap()
        .to_path_buf();
    let outcome = invoke(
        &manifest,
        &directory,
        "add",
        &json!({"left": 20, "right": 22}),
        &policy(&manifest),
    )
    .unwrap();
    assert_eq!(outcome.result, json!(42));

    let error = invoke(
        &manifest,
        &directory,
        "explode",
        &json!({}),
        &policy(&manifest),
    )
    .unwrap_err();
    assert_eq!(error.code, "I0011");
    assert_eq!(error.detail.unwrap()["data"]["kind"], "ValueError");

    let mut timeout_policy = policy(&manifest);
    timeout_policy.timeout = Duration::from_millis(30);
    timeout_policy.allowed_effects.insert("clock".to_owned());
    let started = Instant::now();
    let error = invoke(
        &manifest,
        &directory,
        "sleep_ms",
        &json!({"milliseconds": 500}),
        &timeout_policy,
    )
    .unwrap_err();
    assert_eq!(error.code, "I0008");
    assert!(started.elapsed() < Duration::from_secs(1));
    #[cfg(target_os = "linux")]
    {
        let pid = error.detail.unwrap()["pid"].as_u64().unwrap();
        assert!(!Path::new(&format!("/proc/{pid}")).exists());
    }
}

#[test]
fn rejects_denied_undeclared_and_invalid_worker_behavior() {
    let manifest = load("python");
    let manifest_path = example("python", "manifest.json");
    let directory = manifest_path.parent().unwrap();
    assert_eq!(
        invoke(
            &manifest,
            directory,
            "sleep_ms",
            &json!({"milliseconds": 1}),
            &policy(&manifest),
        )
        .unwrap_err()
        .code,
        "I0005"
    );
    let mut requires_capability = manifest.clone();
    requires_capability.exports[0]
        .capabilities
        .push("filesystem".to_owned());
    assert_eq!(
        invoke(
            &requires_capability,
            directory,
            "add",
            &json!({"left": 20, "right": 22}),
            &policy(&requires_capability),
        )
        .unwrap_err()
        .code,
        "I0006"
    );

    let mut undeclared = manifest.clone();
    undeclared.transport.command = python_response(
        r#"{"jsonrpc":"2.0","id":1,"result":42,"meta":{"effects":["network"],"capabilities":[]}}"#,
    );
    let mut granted = policy(&undeclared);
    granted.allowed_effects.insert("network".to_owned());
    assert_eq!(
        invoke(
            &undeclared,
            directory,
            "add",
            &json!({"left": 20, "right": 22}),
            &granted,
        )
        .unwrap_err()
        .code,
        "I0013"
    );

    let mut malformed = manifest;
    malformed.transport.command = python_response("not-json");
    assert_eq!(
        invoke(
            &malformed,
            directory,
            "add",
            &json!({"left": 20, "right": 22}),
            &policy(&malformed),
        )
        .unwrap_err()
        .code,
        "I0010"
    );

    let mut wrong_type = malformed.clone();
    wrong_type.transport.command = python_response(
        r#"{"jsonrpc":"2.0","id":1,"result":"forty-two","meta":{"effects":[],"capabilities":[]}}"#,
    );
    assert_eq!(
        invoke(
            &wrong_type,
            directory,
            "add",
            &json!({"left": 20, "right": 22}),
            &policy(&wrong_type),
        )
        .unwrap_err()
        .code,
        "I0012"
    );

    let mut exited = malformed;
    exited.transport.command = vec![
        "python3".to_owned(),
        "-c".to_owned(),
        "import sys;sys.stdin.readline();sys.exit(7)".to_owned(),
    ];
    assert_eq!(
        invoke(
            &exited,
            directory,
            "add",
            &json!({"left": 20, "right": 22}),
            &policy(&exited),
        )
        .unwrap_err()
        .code,
        "I0009"
    );
}

#[test]
fn go_and_rust_workers_use_the_same_protocol() {
    let temporary = std::env::temp_dir();
    let go_binary = temporary.join(format!("tacitra-go-worker-{}", std::process::id()));
    let go_cache = temporary.join(format!("tacitra-go-cache-{}", std::process::id()));
    let go_status = Command::new("go")
        .args(["build", "-o"])
        .arg(&go_binary)
        .arg(example("go", "worker.go"))
        .env("GOCACHE", &go_cache)
        .status()
        .expect("Go toolchain is required for the compatibility fixture");
    assert!(go_status.success());

    let rust_binary = temporary.join(format!("tacitra-rust-worker-{}", std::process::id()));
    let rustc = Path::new(env!("CARGO")).with_file_name("rustc");
    let rust_status = Command::new(rustc)
        .args(["--edition=2021"])
        .arg(example("rust", "worker.rs"))
        .arg("-o")
        .arg(&rust_binary)
        .status()
        .unwrap();
    assert!(rust_status.success());

    for (language, binary) in [("go", &go_binary), ("rust", &rust_binary)] {
        let mut manifest = load(language);
        manifest.transport.command = vec![binary.to_string_lossy().into_owned()];
        let outcome = invoke(
            &manifest,
            Path::new("/tmp"),
            "add",
            &json!({"left": 20, "right": 22}),
            &policy(&manifest),
        )
        .unwrap();
        assert_eq!(outcome.result, json!(42));
    }
    let _ = fs::remove_file(go_binary);
    let _ = fs::remove_file(rust_binary);
}

fn python_response(response: &str) -> Vec<String> {
    vec![
        "python3".to_owned(),
        "-c".to_owned(),
        format!("import sys;sys.stdin.readline();print({response:?})"),
    ]
}
