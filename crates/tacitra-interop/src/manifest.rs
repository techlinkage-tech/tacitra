use crate::{validate_value, InteropError};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeSet;

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub schema_version: u32,
    pub module: String,
    pub transport: Transport,
    pub exports: Vec<Export>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Transport {
    pub kind: TransportKind,
    pub protocol_version: String,
    pub command: Vec<String>,
    pub timeout_ms: u64,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
pub enum TransportKind {
    #[serde(rename = "stdio-json-rpc")]
    StdioJsonRpc,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Export {
    pub name: String,
    pub parameters: Vec<Parameter>,
    pub result: ExternalType,
    pub error: Option<ExternalType>,
    pub mode: CallMode,
    pub effects: Vec<String>,
    pub capabilities: Vec<String>,
    pub ownership: Ownership,
    pub examples: Vec<UsageExample>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Parameter {
    pub name: String,
    #[serde(rename = "type")]
    pub ty: ExternalType,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ManifestField {
    pub name: String,
    #[serde(rename = "type")]
    pub ty: ExternalType,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct UsageExample {
    pub description: String,
    pub arguments: Value,
    pub result: Value,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CallMode {
    Sync,
    Async,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, Eq, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum Ownership {
    Copy,
    Handle,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum ExternalType {
    Bool,
    Int {
        signed: bool,
        bits: u8,
    },
    Float {
        bits: u8,
    },
    String,
    Bytes,
    List {
        element: Box<ExternalType>,
    },
    Record {
        name: String,
        fields: Vec<ManifestField>,
    },
    Option {
        value: Box<ExternalType>,
    },
    Result {
        ok: Box<ExternalType>,
        error: Box<ExternalType>,
    },
    Opaque {
        name: String,
    },
}

/// Parses and validates a version-one interoperability manifest.
///
/// # Errors
///
/// Returns a stable interoperability error for malformed JSON or an invalid contract.
pub fn parse_manifest(source: &str) -> Result<Manifest, InteropError> {
    let manifest: Manifest = serde_json::from_str(source).map_err(|error| {
        InteropError::new("I0001", format!("invalid manifest JSON: {error}"), None)
    })?;
    validate_manifest(&manifest)?;
    Ok(manifest)
}

/// Checks all version, naming, type, policy, and example invariants.
///
/// # Errors
///
/// Returns the first deterministic validation error in manifest order.
pub fn validate_manifest(manifest: &Manifest) -> Result<(), InteropError> {
    if manifest.schema_version != 1 {
        return Err(InteropError::new(
            "I0002",
            "unsupported manifest schema version",
            Some(serde_json::json!({ "actual": manifest.schema_version, "supported": 1 })),
        ));
    }
    identifier(&manifest.module, "module")?;
    if manifest.transport.protocol_version != "2.0" {
        return Err(invalid("transport.protocol_version must be `2.0`"));
    }
    if !(1..=300_000).contains(&manifest.transport.timeout_ms) {
        return Err(invalid("transport.timeout_ms must be between 1 and 300000"));
    }
    if manifest.transport.command.is_empty()
        || manifest.transport.command.iter().any(String::is_empty)
    {
        return Err(invalid(
            "transport.command must contain non-empty arguments",
        ));
    }
    if manifest.exports.is_empty() {
        return Err(invalid("manifest must declare at least one export"));
    }
    let mut names = BTreeSet::new();
    for export in &manifest.exports {
        identifier(&export.name, "export")?;
        if !names.insert(&export.name) {
            return Err(invalid("duplicate export name"));
        }
        validate_export(export)?;
    }
    Ok(())
}

fn validate_export(export: &Export) -> Result<(), InteropError> {
    let mut parameters = BTreeSet::new();
    let mut has_opaque = false;
    for parameter in &export.parameters {
        identifier(&parameter.name, "parameter")?;
        if !parameters.insert(&parameter.name) {
            return Err(invalid("duplicate parameter name"));
        }
        validate_type(&parameter.ty)?;
        has_opaque |= contains_opaque(&parameter.ty);
    }
    validate_type(&export.result)?;
    has_opaque |= contains_opaque(&export.result);
    if let Some(error) = &export.error {
        validate_type(error)?;
        has_opaque |= contains_opaque(error);
    }
    if has_opaque && export.ownership != Ownership::Handle {
        return Err(invalid(
            "exports containing opaque values must use handle ownership",
        ));
    }
    unique_names(&export.effects, "effect")?;
    unique_names(&export.capabilities, "capability")?;
    if export.examples.is_empty() {
        return Err(invalid("each export must include at least one example"));
    }
    for example in &export.examples {
        if example.description.trim().is_empty() {
            return Err(invalid("example description must not be empty"));
        }
        validate_arguments(export, &example.arguments)?;
        validate_value(&export.result, &example.result, "example.result")?;
    }
    Ok(())
}

pub(crate) fn validate_arguments(export: &Export, value: &Value) -> Result<(), InteropError> {
    let object = value
        .as_object()
        .ok_or_else(|| type_error("arguments must be an object"))?;
    if object.len() != export.parameters.len() {
        return Err(type_error(
            "arguments must exactly match declared parameters",
        ));
    }
    for parameter in &export.parameters {
        let argument = object
            .get(&parameter.name)
            .ok_or_else(|| type_error(&format!("missing argument `{}`", parameter.name)))?;
        validate_value(
            &parameter.ty,
            argument,
            &format!("arguments.{}", parameter.name),
        )?;
    }
    Ok(())
}

fn validate_type(ty: &ExternalType) -> Result<(), InteropError> {
    match ty {
        ExternalType::Int { bits, .. } if !matches!(bits, 8 | 16 | 32 | 64) => {
            Err(invalid("integer width must be 8, 16, 32, or 64"))
        }
        ExternalType::Float { bits } if !matches!(bits, 32 | 64) => {
            Err(invalid("float width must be 32 or 64"))
        }
        ExternalType::List { element } | ExternalType::Option { value: element } => {
            validate_type(element)
        }
        ExternalType::Result { ok, error } => {
            validate_type(ok)?;
            validate_type(error)
        }
        ExternalType::Record { name, fields } => {
            identifier(name, "record type")?;
            let mut names = BTreeSet::new();
            for field in fields {
                identifier(&field.name, "record field")?;
                if !names.insert(&field.name) {
                    return Err(invalid("duplicate record field"));
                }
                validate_type(&field.ty)?;
            }
            Ok(())
        }
        ExternalType::Opaque { name } => identifier(name, "opaque type"),
        _ => Ok(()),
    }
}

fn contains_opaque(ty: &ExternalType) -> bool {
    match ty {
        ExternalType::Opaque { .. } => true,
        ExternalType::List { element } | ExternalType::Option { value: element } => {
            contains_opaque(element)
        }
        ExternalType::Result { ok, error } => contains_opaque(ok) || contains_opaque(error),
        ExternalType::Record { fields, .. } => {
            fields.iter().any(|field| contains_opaque(&field.ty))
        }
        _ => false,
    }
}

fn unique_names(values: &[String], kind: &str) -> Result<(), InteropError> {
    let mut seen = BTreeSet::new();
    for value in values {
        identifier(value, kind)?;
        if !seen.insert(value) {
            return Err(invalid(&format!("duplicate {kind}")));
        }
    }
    Ok(())
}

fn identifier(value: &str, kind: &str) -> Result<(), InteropError> {
    let mut characters = value.chars();
    if !characters
        .next()
        .is_some_and(|character| character.is_ascii_alphabetic() || character == '_')
        || !characters.all(|character| character.is_ascii_alphanumeric() || character == '_')
    {
        return Err(invalid(&format!("invalid {kind} name `{value}`")));
    }
    Ok(())
}

fn invalid(message: &str) -> InteropError {
    InteropError::new("I0001", message, None)
}

fn type_error(message: &str) -> InteropError {
    InteropError::new("I0003", message, None)
}
