use crate::{manifest::validate_arguments, validate_value, Export, InteropError, Manifest};
use serde_json::{json, Map, Value};
use std::{
    collections::BTreeSet,
    io::{Read, Write},
    path::Path,
    process::{Child, Command, Stdio},
    thread,
    time::{Duration, Instant},
};

#[derive(Clone, Debug)]
pub struct InvocationPolicy {
    pub timeout: Duration,
    pub allowed_effects: BTreeSet<String>,
    pub allowed_capabilities: BTreeSet<String>,
}

impl InvocationPolicy {
    #[must_use]
    pub fn from_manifest(manifest: &Manifest) -> Self {
        Self {
            timeout: Duration::from_millis(manifest.transport.timeout_ms),
            allowed_effects: BTreeSet::new(),
            allowed_capabilities: BTreeSet::new(),
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct CallOutcome {
    pub result: Value,
    pub observed_effects: Vec<String>,
    pub observed_capabilities: Vec<String>,
}

impl CallOutcome {
    #[must_use]
    pub fn to_json(&self) -> String {
        serde_json::to_string(&json!({
            "valid": true,
            "result": self.result,
            "observed_effects": self.observed_effects,
            "observed_capabilities": self.observed_capabilities,
        }))
        .unwrap_or_default()
    }
}

/// Invokes one manifest export through a fresh JSON-RPC child process.
///
/// # Errors
///
/// Returns stable errors for policy denial, process, timeout, protocol, external, and type failures.
pub fn invoke(
    manifest: &Manifest,
    working_directory: &Path,
    export_name: &str,
    arguments: &Value,
    policy: &InvocationPolicy,
) -> Result<CallOutcome, InteropError> {
    let export = manifest
        .exports
        .iter()
        .find(|export| export.name == export_name)
        .ok_or_else(|| {
            InteropError::new(
                "I0004",
                format!("external export `{export_name}` does not exist"),
                Some(json!({ "export": export_name })),
            )
        })?;
    validate_arguments(export, arguments)?;
    require_grants(export, policy)?;
    let request = serde_json::to_vec(&json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": export.name,
        "params": arguments,
    }))
    .map_err(|error| InteropError::new("I0010", error.to_string(), None))?;
    let command = &manifest.transport.command;
    let mut child = Command::new(&command[0])
        .args(&command[1..])
        .current_dir(working_directory)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| {
            InteropError::new(
                "I0007",
                format!("failed to start external worker: {error}"),
                None,
            )
        })?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| process_error("stdout unavailable"))?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| process_error("stderr unavailable"))?;
    let stdout_reader = thread::spawn(move || read_all(stdout));
    let stderr_reader = thread::spawn(move || read_all(stderr));
    let write_result = child
        .stdin
        .take()
        .ok_or_else(|| process_error("stdin unavailable"))
        .and_then(|mut stdin| {
            stdin
                .write_all(&request)
                .and_then(|()| stdin.write_all(b"\n"))
                .map_err(|error| process_error(&format!("failed to write request: {error}")))
        });
    if let Err(error) = write_result {
        terminate(&mut child);
        let _ = stdout_reader.join();
        let _ = stderr_reader.join();
        return Err(error);
    }
    let status = match wait_until(&mut child, policy.timeout) {
        Ok(status) => status,
        Err(error) => {
            terminate(&mut child);
            let _ = stdout_reader.join();
            let _ = stderr_reader.join();
            return Err(error);
        }
    };
    let stdout = join_reader(stdout_reader)?;
    let stderr = join_reader(stderr_reader)?;
    if !status.success() {
        return Err(InteropError::new(
            "I0009",
            "external worker exited unsuccessfully",
            Some(json!({
                "status": status.code(),
                "stderr": bounded_text(&stderr),
            })),
        ));
    }
    parse_response(export, &stdout, policy)
}

fn wait_until(
    child: &mut Child,
    timeout: Duration,
) -> Result<std::process::ExitStatus, InteropError> {
    let started = Instant::now();
    loop {
        if let Some(status) = child
            .try_wait()
            .map_err(|error| process_error(&format!("failed to wait for worker: {error}")))?
        {
            return Ok(status);
        }
        if started.elapsed() >= timeout {
            let pid = child.id();
            return Err(InteropError::new(
                "I0008",
                "external call timed out",
                Some(json!({ "timeout_ms": timeout.as_millis(), "pid": pid })),
            ));
        }
        thread::sleep(Duration::from_millis(2));
    }
}

fn terminate(child: &mut Child) {
    let _ = child.kill();
    let _ = child.wait();
}

fn read_all(mut reader: impl Read) -> std::io::Result<Vec<u8>> {
    let mut bytes = Vec::new();
    reader.read_to_end(&mut bytes)?;
    Ok(bytes)
}

fn join_reader(
    reader: thread::JoinHandle<std::io::Result<Vec<u8>>>,
) -> Result<Vec<u8>, InteropError> {
    reader
        .join()
        .map_err(|_| process_error("worker output reader panicked"))?
        .map_err(|error| process_error(&format!("failed to read worker output: {error}")))
}

fn parse_response(
    export: &Export,
    stdout: &[u8],
    policy: &InvocationPolicy,
) -> Result<CallOutcome, InteropError> {
    let response: Value = serde_json::from_slice(stdout).map_err(|error| {
        protocol_error(&format!("worker returned invalid JSON: {error}"), stdout)
    })?;
    let object = response
        .as_object()
        .ok_or_else(|| protocol_error("response must be an object", stdout))?;
    let allowed = ["jsonrpc", "id", "result", "error", "meta"];
    if object.keys().any(|key| !allowed.contains(&key.as_str()))
        || object.get("jsonrpc").and_then(Value::as_str) != Some("2.0")
        || object.get("id").and_then(Value::as_u64) != Some(1)
        || object.contains_key("result") == object.contains_key("error")
    {
        return Err(protocol_error("invalid JSON-RPC response envelope", stdout));
    }
    let (effects, capabilities) = parse_meta(object.get("meta"), stdout)?;
    validate_observed(export, &effects, &capabilities, policy)?;
    if let Some(error) = object.get("error") {
        return external_error(export, error);
    }
    let result = object.get("result").expect("response shape checked");
    validate_value(&export.result, result, "response.result").map_err(|error| {
        InteropError::new(
            "I0012",
            "external result does not match the manifest",
            error.detail,
        )
    })?;
    Ok(CallOutcome {
        result: result.clone(),
        observed_effects: effects,
        observed_capabilities: capabilities,
    })
}

fn parse_meta(
    meta: Option<&Value>,
    raw: &[u8],
) -> Result<(Vec<String>, Vec<String>), InteropError> {
    let Some(meta) = meta else {
        return Ok((Vec::new(), Vec::new()));
    };
    let object = meta
        .as_object()
        .ok_or_else(|| protocol_error("response meta must be an object", raw))?;
    if object
        .keys()
        .any(|key| key != "effects" && key != "capabilities")
    {
        return Err(protocol_error("response meta has unknown fields", raw));
    }
    Ok((
        string_array(object, "effects", raw)?,
        string_array(object, "capabilities", raw)?,
    ))
}

fn string_array(
    object: &Map<String, Value>,
    name: &str,
    raw: &[u8],
) -> Result<Vec<String>, InteropError> {
    let Some(value) = object.get(name) else {
        return Ok(Vec::new());
    };
    let values = value
        .as_array()
        .ok_or_else(|| protocol_error("response metadata must contain string arrays", raw))?;
    let mut result = Vec::new();
    for value in values {
        let name = value
            .as_str()
            .ok_or_else(|| protocol_error("response metadata must contain strings", raw))?;
        result.push(name.to_owned());
    }
    result.sort();
    result.dedup();
    Ok(result)
}

fn external_error(export: &Export, value: &Value) -> Result<CallOutcome, InteropError> {
    let object = value
        .as_object()
        .ok_or_else(|| protocol_error("JSON-RPC error must be an object", b""))?;
    let code = object.get("code").and_then(Value::as_i64);
    let message = object.get("message").and_then(Value::as_str);
    if code.is_none()
        || message.is_none()
        || object
            .keys()
            .any(|key| key != "code" && key != "message" && key != "data")
    {
        return Err(protocol_error("invalid JSON-RPC error object", b""));
    }
    let data = object.get("data").cloned().unwrap_or(Value::Null);
    if let Some(error_type) = &export.error {
        validate_value(error_type, &data, "response.error.data").map_err(|error| {
            InteropError::new(
                "I0010",
                "external error data does not match the manifest",
                error.detail,
            )
        })?;
    }
    Err(InteropError::new(
        "I0011",
        message.unwrap_or_default(),
        Some(json!({ "external_code": code, "data": data })),
    ))
}

fn require_grants(export: &Export, policy: &InvocationPolicy) -> Result<(), InteropError> {
    if let Some(effect) = export
        .effects
        .iter()
        .find(|effect| !policy.allowed_effects.contains(*effect))
    {
        return Err(InteropError::new(
            "I0005",
            format!("effect `{effect}` is not allowed"),
            Some(json!({ "effect": effect })),
        ));
    }
    if let Some(capability) = export
        .capabilities
        .iter()
        .find(|capability| !policy.allowed_capabilities.contains(*capability))
    {
        return Err(InteropError::new(
            "I0006",
            format!("capability `{capability}` is not allowed"),
            Some(json!({ "capability": capability })),
        ));
    }
    Ok(())
}

fn validate_observed(
    export: &Export,
    effects: &[String],
    capabilities: &[String],
    policy: &InvocationPolicy,
) -> Result<(), InteropError> {
    let declared_effects = export.effects.iter().collect::<BTreeSet<_>>();
    let declared_capabilities = export.capabilities.iter().collect::<BTreeSet<_>>();
    let unexpected_effects = effects
        .iter()
        .filter(|effect| !declared_effects.contains(effect))
        .cloned()
        .collect::<Vec<_>>();
    let unexpected_capabilities = capabilities
        .iter()
        .filter(|capability| !declared_capabilities.contains(capability))
        .cloned()
        .collect::<Vec<_>>();
    if !unexpected_effects.is_empty() || !unexpected_capabilities.is_empty() {
        return Err(InteropError::new(
            "I0013",
            "worker reported undeclared effects or capabilities",
            Some(json!({
                "effects": unexpected_effects,
                "capabilities": unexpected_capabilities,
            })),
        ));
    }
    if effects
        .iter()
        .any(|effect| !policy.allowed_effects.contains(effect))
        || capabilities
            .iter()
            .any(|capability| !policy.allowed_capabilities.contains(capability))
    {
        return Err(InteropError::new(
            "I0013",
            "worker reported activity outside the invocation grant",
            None,
        ));
    }
    Ok(())
}

fn process_error(message: &str) -> InteropError {
    InteropError::new("I0007", message, None)
}

fn protocol_error(message: &str, raw: &[u8]) -> InteropError {
    InteropError::new(
        "I0010",
        message,
        Some(json!({ "response": bounded_text(raw) })),
    )
}

fn bounded_text(bytes: &[u8]) -> String {
    String::from_utf8_lossy(&bytes[..bytes.len().min(4096)]).into_owned()
}
