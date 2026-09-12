use crate::{
    ai::TypedEditDocument,
    patch::{PatchOperation, PatchOperationKind},
    AgentError,
};
use serde_json::{Map, Value};

/// Parses the readable, named typed-edit v1 representation.
///
/// # Errors
///
/// Returns `A0008` for malformed or unsupported documents.
pub fn parse_named_typed_edit(source: &str) -> Result<TypedEditDocument, AgentError> {
    let value: Value = serde_json::from_str(source)
        .map_err(|error| schema_error(format!("invalid named-edit JSON: {error}")))?;
    let object = value
        .as_object()
        .ok_or_else(|| schema_error("named edit must be an object"))?;
    require_keys(
        object,
        &["version", "base_hash", "capabilities", "operations"],
    )?;
    let version = object
        .get("version")
        .and_then(Value::as_u64)
        .ok_or_else(|| schema_error("`version` must be an integer"))?;
    if version != 1 {
        return Err(schema_error("unsupported named-edit version"));
    }
    let base_hash = object
        .get("base_hash")
        .and_then(Value::as_str)
        .filter(|value| valid_hash(value))
        .ok_or_else(|| schema_error("`base_hash` must be a lowercase SHA-256 digest"))?
        .to_owned();
    let capabilities = object
        .get("capabilities")
        .and_then(Value::as_array)
        .ok_or_else(|| schema_error("`capabilities` must be an array"))?
        .iter()
        .map(|value| {
            value
                .as_str()
                .map(str::to_owned)
                .ok_or_else(|| schema_error("capabilities must be strings"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let rows = object
        .get("operations")
        .and_then(Value::as_array)
        .filter(|rows| !rows.is_empty())
        .ok_or_else(|| schema_error("`operations` must be a non-empty array"))?;
    let mut operations = Vec::new();
    for row in rows {
        let row = row
            .as_object()
            .ok_or_else(|| schema_error("operation must be an object"))?;
        require_keys(row, &["operation", "target", "replacement"])?;
        let op = match row.get("operation").and_then(Value::as_str) {
            Some("replace_function_body") => PatchOperationKind::ReplaceFunctionBody,
            Some("replace_expression") => PatchOperationKind::ReplaceExpression,
            Some(value) => return Err(schema_error(format!("unsupported operation `{value}`"))),
            None => return Err(schema_error("`operation` must be a string")),
        };
        let target = row
            .get("target")
            .and_then(Value::as_str)
            .filter(|value| !value.is_empty())
            .ok_or_else(|| schema_error("operation target must be a non-empty string"))?;
        let replacement = row
            .get("replacement")
            .and_then(Value::as_str)
            .ok_or_else(|| schema_error("operation replacement must be a string"))?;
        operations.push(PatchOperation {
            op,
            target: target.to_owned(),
            replacement: replacement.to_owned(),
        });
    }
    Ok(TypedEditDocument {
        version,
        base_hash,
        capabilities,
        operations,
    })
}

/// Binds an ordinary Tacitra function-body fragment to a semantic target.
#[must_use]
pub fn function_body_edit(base_hash: &str, target: &str, replacement: &str) -> TypedEditDocument {
    TypedEditDocument {
        version: 1,
        base_hash: base_hash.to_owned(),
        capabilities: Vec::new(),
        operations: vec![PatchOperation {
            op: PatchOperationKind::ReplaceFunctionBody,
            target: target.to_owned(),
            replacement: replacement.to_owned(),
        }],
    }
}

fn require_keys(object: &Map<String, Value>, expected: &[&str]) -> Result<(), AgentError> {
    if let Some(key) = expected.iter().find(|key| !object.contains_key(**key)) {
        return Err(schema_error(format!("missing `{key}`")));
    }
    if let Some(key) = object.keys().find(|key| !expected.contains(&key.as_str())) {
        return Err(schema_error(format!("unknown field `{key}`")));
    }
    Ok(())
}

fn schema_error(message: impl Into<String>) -> AgentError {
    AgentError::new("A0008", message, None)
}

fn valid_hash(value: &str) -> bool {
    value.strip_prefix("sha256:").is_some_and(|digest| {
        digest.len() == 64
            && digest
                .chars()
                .all(|character| character.is_ascii_hexdigit() && !character.is_ascii_uppercase())
    })
}
