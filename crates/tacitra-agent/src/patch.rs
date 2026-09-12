use crate::model::{hash_text, AgentError, PatchTargetKind, SemanticModule};
use serde_json::{json, Map, Value};
use std::collections::BTreeSet;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PatchDocument {
    pub schema_version: u64,
    pub base_hash: String,
    pub operations: Vec<PatchOperation>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PatchOperation {
    pub op: PatchOperationKind,
    pub target: String,
    pub replacement: String,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PatchOperationKind {
    ReplaceFunctionBody,
    ReplaceExpression,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PatchOutcome {
    pub base_hash: String,
    pub result_hash: String,
    pub updated_source: String,
    pub diff: String,
    pub descriptions: Vec<String>,
    pub changed: bool,
}

impl PatchOutcome {
    #[must_use]
    pub fn to_json(&self) -> String {
        serde_json::to_string(&json!({
            "base_hash": self.base_hash, "changed": self.changed, "diff": self.diff,
            "operations": self.descriptions, "result_hash": self.result_hash,
            "schema_version": 1, "valid": true
        }))
        .unwrap_or_default()
    }
}

/// Parses and strictly validates a version-one structural patch document.
///
/// # Errors
///
/// Returns `A0006` when JSON or its schema is invalid.
pub fn parse_patch(source: &str) -> Result<PatchDocument, AgentError> {
    let value: Value = serde_json::from_str(source)
        .map_err(|error| AgentError::new("A0006", format!("invalid patch JSON: {error}"), None))?;
    let object = value
        .as_object()
        .ok_or_else(|| schema_error("patch must be an object"))?;
    require_keys(object, &["schema_version", "base_hash", "operations"])?;
    let schema_version = object
        .get("schema_version")
        .and_then(Value::as_u64)
        .ok_or_else(|| schema_error("`schema_version` must be an integer"))?;
    if schema_version != 1 {
        return Err(schema_error("unsupported patch schema version"));
    }
    let base_hash = object
        .get("base_hash")
        .and_then(Value::as_str)
        .ok_or_else(|| schema_error("`base_hash` must be a string"))?
        .to_owned();
    let valid_hash = base_hash.strip_prefix("sha256:").is_some_and(|value| {
        value.len() == 64
            && value
                .chars()
                .all(|character| character.is_ascii_hexdigit() && !character.is_ascii_uppercase())
    });
    if !valid_hash {
        return Err(schema_error(
            "`base_hash` must be a lowercase SHA-256 digest",
        ));
    }
    let operation_values = object
        .get("operations")
        .and_then(Value::as_array)
        .ok_or_else(|| schema_error("`operations` must be an array"))?;
    if operation_values.is_empty() {
        return Err(schema_error("`operations` must not be empty"));
    }
    let mut operations = Vec::new();
    for value in operation_values {
        let operation = value
            .as_object()
            .ok_or_else(|| schema_error("operation must be an object"))?;
        require_keys(operation, &["op", "target", "replacement"])?;
        let op = match operation.get("op").and_then(Value::as_str) {
            Some("replace_function_body") => PatchOperationKind::ReplaceFunctionBody,
            Some("replace_expression") => PatchOperationKind::ReplaceExpression,
            Some(value) => return Err(schema_error(&format!("unsupported operation `{value}`"))),
            None => return Err(schema_error("`op` must be a string")),
        };
        let target = operation
            .get("target")
            .and_then(Value::as_str)
            .ok_or_else(|| schema_error("`target` must be a string"))?
            .to_owned();
        if target.is_empty() {
            return Err(schema_error("`target` must not be empty"));
        }
        let replacement = operation
            .get("replacement")
            .and_then(Value::as_str)
            .ok_or_else(|| schema_error("`replacement` must be a string"))?
            .to_owned();
        operations.push(PatchOperation {
            op,
            target,
            replacement,
        });
    }
    Ok(PatchDocument {
        schema_version,
        base_hash,
        operations,
    })
}

/// Validates a patch against the indexed module without mutating files.
///
/// # Errors
///
/// Rejects stale, missing, ambiguous, overlapping, kind-invalid, or compiler-invalid changes.
pub fn validate_patch(
    module: &SemanticModule,
    patch: &PatchDocument,
) -> Result<PatchOutcome, AgentError> {
    evaluate_patch(module, patch)
}

/// Produces the checked replacement source and reviewable diff for a patch.
///
/// This library function does not write files; the CLI performs the explicit write after success.
///
/// # Errors
///
/// Rejects stale, missing, ambiguous, overlapping, kind-invalid, or compiler-invalid changes.
pub fn apply_patch(
    module: &SemanticModule,
    patch: &PatchDocument,
) -> Result<PatchOutcome, AgentError> {
    evaluate_patch(module, patch)
}

fn evaluate_patch(
    module: &SemanticModule,
    patch: &PatchDocument,
) -> Result<PatchOutcome, AgentError> {
    if patch.base_hash != module.content_hash {
        return Err(AgentError::new(
            "A0003",
            format!(
                "stale patch: expected {}, found {}",
                patch.base_hash, module.content_hash
            ),
            None,
        ));
    }
    let mut edits = Vec::new();
    let mut descriptions = Vec::new();
    for operation in &patch.operations {
        let target = module.resolve_patch_target(&operation.target)?;
        let compatible = matches!(
            (operation.op, target.kind),
            (
                PatchOperationKind::ReplaceFunctionBody,
                PatchTargetKind::FunctionBody
            ) | (
                PatchOperationKind::ReplaceExpression,
                PatchTargetKind::Expression
            )
        );
        if !compatible {
            return Err(AgentError::new(
                "A0007",
                "operation does not match target kind",
                Some(target.id),
            ));
        }
        let description = match operation.op {
            PatchOperationKind::ReplaceFunctionBody => {
                format!("replace body of function `{}`", target.name)
            }
            PatchOperationKind::ReplaceExpression => format!("replace expression `{}`", target.id),
        };
        descriptions.push(description);
        edits.push((
            target.span.start.byte,
            target.span.end.byte,
            operation.replacement.clone(),
            target.id,
        ));
    }
    edits.sort_by_key(|edit| edit.0);
    for pair in edits.windows(2) {
        if pair[0].1 > pair[1].0 {
            return Err(AgentError::new(
                "A0004",
                "patch operations overlap",
                Some(pair[1].3.clone()),
            ));
        }
    }
    let mut changed_source = module.source.clone();
    for (start, end, replacement, _) in edits.iter().rev() {
        changed_source.replace_range(*start..*end, replacement);
    }
    let updated = SemanticModule::build(&changed_source).map_err(|diagnostics| {
        let codes = diagnostics
            .iter()
            .map(|value| value.code)
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect::<Vec<_>>()
            .join(", ");
        let error = AgentError::new(
            "A0005",
            format!("patched module does not compile: {codes}"),
            None,
        );
        diagnostics.first().map_or(error.clone(), |diagnostic| {
            error.with_diagnostic(diagnostic)
        })
    })?;
    let updated_source = updated.canonical_source.clone();
    let changed = updated_source != module.canonical_source;
    Ok(PatchOutcome {
        base_hash: module.content_hash.clone(),
        result_hash: hash_text(&updated_source),
        diff: unified_diff(&module.canonical_source, &updated_source),
        updated_source,
        descriptions,
        changed,
    })
}

fn require_keys(object: &Map<String, Value>, expected: &[&str]) -> Result<(), AgentError> {
    for key in expected {
        if !object.contains_key(*key) {
            return Err(schema_error(&format!("missing `{key}`")));
        }
    }
    if let Some(key) = object.keys().find(|key| !expected.contains(&key.as_str())) {
        return Err(schema_error(&format!("unknown field `{key}`")));
    }
    Ok(())
}

fn schema_error(message: &str) -> AgentError {
    AgentError::new("A0006", message, None)
}

fn unified_diff(old: &str, new: &str) -> String {
    if old == new {
        return String::new();
    }
    let old_lines = old.lines().collect::<Vec<_>>();
    let new_lines = new.lines().collect::<Vec<_>>();
    let prefix = old_lines
        .iter()
        .zip(&new_lines)
        .take_while(|(left, right)| left == right)
        .count();
    let max_suffix = old_lines.len().min(new_lines.len()).saturating_sub(prefix);
    let suffix = (0..max_suffix)
        .take_while(|offset| {
            old_lines[old_lines.len() - 1 - offset] == new_lines[new_lines.len() - 1 - offset]
        })
        .count();
    let old_changed = &old_lines[prefix..old_lines.len() - suffix];
    let new_changed = &new_lines[prefix..new_lines.len() - suffix];
    let mut output = format!(
        "--- a/module.taci\n+++ b/module.taci\n@@ -{},{} +{},{} @@\n",
        prefix + 1,
        old_changed.len(),
        prefix + 1,
        new_changed.len()
    );
    for line in old_changed {
        output.push('-');
        output.push_str(line);
        output.push('\n');
    }
    for line in new_changed {
        output.push('+');
        output.push_str(line);
        output.push('\n');
    }
    output
}
