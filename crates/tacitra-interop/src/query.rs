use crate::{Export, Manifest};
use serde_json::{json, Value};

#[must_use]
pub fn manifest_summary(manifest: &Manifest) -> String {
    let mut exports = manifest.exports.iter().map(export_json).collect::<Vec<_>>();
    exports.sort_by(|left, right| left["name"].as_str().cmp(&right["name"].as_str()));
    serialize(&json!({
        "schema_version": manifest.schema_version,
        "module": manifest.module,
        "transport": {
            "kind": manifest.transport.kind,
            "protocol_version": manifest.transport.protocol_version,
            "timeout_ms": manifest.transport.timeout_ms,
        },
        "exports": exports,
    }))
}

/// Describes one external function without returning worker source or a launch command.
///
/// # Errors
///
/// Returns `I0004` when the manifest has no export with the exact name.
pub fn export_describe(manifest: &Manifest, name: &str) -> Result<String, crate::InteropError> {
    let export = manifest
        .exports
        .iter()
        .find(|export| export.name == name)
        .ok_or_else(|| {
            crate::InteropError::new(
                "I0004",
                format!("external export `{name}` does not exist"),
                Some(json!({ "export": name })),
            )
        })?;
    Ok(serialize(&json!({
        "module": manifest.module,
        "export": export_json(export),
    })))
}

/// Returns one export's execution contract without unrelated exports or launch details.
///
/// # Errors
///
/// Returns `I0004` when the exact export name does not exist.
pub fn call_context(manifest: &Manifest, name: &str) -> Result<String, crate::InteropError> {
    let export = find_export(manifest, name)?;
    Ok(serialize(&json!({
        "capabilities": export.capabilities,
        "effects": export.effects,
        "error": export.error,
        "example": export.examples.first(),
        "mode": export.mode,
        "module": manifest.module,
        "name": export.name,
        "ownership": export.ownership,
        "parameters": export.parameters,
        "result": export.result,
    })))
}

fn find_export<'a>(manifest: &'a Manifest, name: &str) -> Result<&'a Export, crate::InteropError> {
    manifest
        .exports
        .iter()
        .find(|export| export.name == name)
        .ok_or_else(|| {
            crate::InteropError::new(
                "I0004",
                format!("external export `{name}` does not exist"),
                Some(json!({ "export": name })),
            )
        })
}

fn export_json(export: &Export) -> Value {
    json!({
        "name": export.name,
        "parameters": export.parameters,
        "result": export.result,
        "error": export.error,
        "mode": export.mode,
        "effects": export.effects,
        "capabilities": export.capabilities,
        "ownership": export.ownership,
        "examples": export.examples,
    })
}

fn serialize(value: &Value) -> String {
    serde_json::to_string(value).unwrap_or_default()
}
