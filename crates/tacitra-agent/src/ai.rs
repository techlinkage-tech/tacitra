use crate::{
    apply_patch, parse_patch,
    patch::{PatchOperation, PatchOperationKind},
    validate_patch, AgentError, PatchDocument, PatchOutcome, SemanticModule,
};
use serde_json::{json, Map, Value};
use std::collections::BTreeSet;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TypedEditDocument {
    pub version: u64,
    pub base_hash: String,
    pub capabilities: Vec<String>,
    pub operations: Vec<PatchOperation>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepairContext {
    pub code: &'static str,
    pub operation: Option<usize>,
    pub target: Option<String>,
    pub expected_type: Option<String>,
    pub actual_type: Option<String>,
    pub available_values: Vec<(String, String)>,
    pub allowed_operations: Vec<&'static str>,
    pub current_hash: String,
    pub retryable: bool,
}

impl RepairContext {
    #[must_use]
    pub fn to_json(&self) -> String {
        let values = self
            .available_values
            .iter()
            .map(|(id, ty)| json!([id, ty]))
            .collect::<Vec<_>>();
        serde_json::to_string(&json!({
            "v": 1,
            "code": self.code,
            "op": self.operation,
            "target": self.target,
            "expected": self.expected_type,
            "actual": self.actual_type,
            "values": values,
            "allowed": self.allowed_operations,
            "hash": self.current_hash,
            "retry": self.retryable,
        }))
        .unwrap_or_default()
    }
}

/// Produces a deterministic, source-free task capsule for one function edit.
///
/// # Errors
///
/// Returns a stable agent error when the selector is missing, ambiguous, or not a function.
pub fn task_context_capsule(
    module: &SemanticModule,
    selector: &str,
    success: &str,
) -> Result<String, AgentError> {
    let symbol = module.resolve_symbol(selector)?;
    if symbol.kind != "function" {
        return Err(AgentError::new(
            "A0007",
            "task context requires a function symbol",
            Some(symbol.id.clone()),
        ));
    }
    let owner = &symbol.id;
    let mut values = module
        .symbols
        .iter()
        .filter(|value| {
            value.id.starts_with(&format!("{owner}/param:"))
                || value
                    .detail
                    .get("owner")
                    .and_then(Value::as_str)
                    .is_some_and(|value| value == owner)
        })
        .map(|value| json!([value.id, value.ty]))
        .collect::<Vec<_>>();
    values.sort_by_key(ToString::to_string);

    let mut callees = module
        .calls
        .iter()
        .filter(|call| call.caller == *owner)
        .filter_map(|call| {
            module
                .symbols
                .iter()
                .find(|value| value.id == call.callee)
                .map(|value| json!([value.id, value.ty]))
        })
        .collect::<Vec<_>>();
    callees.sort_by_key(ToString::to_string);
    callees.dedup();

    let mut type_names = BTreeSet::new();
    collect_type_names(&symbol.ty, &mut type_names);
    for value in &values {
        if let Some(ty) = value.get(1).and_then(Value::as_str) {
            collect_type_names(ty, &mut type_names);
        }
    }
    for value in &callees {
        if let Some(ty) = value.get(1).and_then(Value::as_str) {
            collect_type_names(ty, &mut type_names);
        }
    }
    let types = module
        .types
        .iter()
        .filter(|value| type_names.contains(&value.name) && value.kind != "builtin")
        .map(|value| json!({"id": value.id, "kind": value.kind, "def": value.detail}))
        .collect::<Vec<_>>();

    Ok(serde_json::to_string(&json!({
        "v": 1,
        "hash": module.content_hash,
        "target": {
            "id": symbol.id,
            "type": symbol.ty,
            "params": symbol.detail["parameters"],
            "return": symbol.detail["return_type"],
            "failure": symbol.detail["failure_type"],
        },
        "values": values,
        "types": types,
        "calls": callees,
        "effects": symbol.detail["effects"],
        "capabilities": [],
        "contracts": symbol.detail["contracts"],
        "allowed": ["body", "expr"],
        "success": success,
    }))
    .unwrap_or_default())
}

/// Returns deterministic UTF-8 byte sizes for each capsule section.
///
/// # Errors
///
/// Returns the same selection errors as [`task_context_capsule`].
///
/// # Panics
///
/// Panics only if the capsule produced internally by [`task_context_capsule`] is
/// not a JSON object, which would indicate a compiler invariant violation.
pub fn task_context_size(
    module: &SemanticModule,
    selector: &str,
    success: &str,
) -> Result<String, AgentError> {
    let capsule = task_context_capsule(module, selector, success)?;
    let value: Value = serde_json::from_str(&capsule).expect("capsule is JSON");
    let object = value.as_object().expect("capsule is object");
    let sections = object
        .iter()
        .map(|(key, value)| {
            (
                key.clone(),
                json!(serde_json::to_string(value).unwrap_or_default().len()),
            )
        })
        .collect::<Map<_, _>>();
    Ok(serde_json::to_string(&json!({
        "evidence": "measured",
        "tokenizer": "utf8-bytes/1",
        "sections": sections,
        "total": capsule.len(),
    }))
    .unwrap_or_default())
}

/// Parses the compact typed-edit v1 tuple representation.
///
/// # Errors
///
/// Returns `A0008` for malformed or unsupported documents.
pub fn parse_typed_edit(source: &str) -> Result<TypedEditDocument, AgentError> {
    let value: Value = serde_json::from_str(source)
        .map_err(|error| typed_schema_error(format!("invalid typed-edit JSON: {error}")))?;
    let object = value
        .as_object()
        .ok_or_else(|| typed_schema_error("typed edit must be an object"))?;
    require_keys(object, &["v", "h", "cap", "ops"])?;
    let version = object
        .get("v")
        .and_then(Value::as_u64)
        .ok_or_else(|| typed_schema_error("`v` must be an integer"))?;
    if version != 1 {
        return Err(typed_schema_error("unsupported typed-edit version"));
    }
    let base_hash = object
        .get("h")
        .and_then(Value::as_str)
        .ok_or_else(|| typed_schema_error("`h` must be a string"))?
        .to_owned();
    if !valid_hash(&base_hash) {
        return Err(typed_schema_error("`h` must be a lowercase SHA-256 digest"));
    }
    let capabilities = object
        .get("cap")
        .and_then(Value::as_array)
        .ok_or_else(|| typed_schema_error("`cap` must be an array"))?
        .iter()
        .map(|value| {
            value
                .as_str()
                .map(str::to_owned)
                .ok_or_else(|| typed_schema_error("capabilities must be strings"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let rows = object
        .get("ops")
        .and_then(Value::as_array)
        .ok_or_else(|| typed_schema_error("`ops` must be an array"))?;
    if rows.is_empty() {
        return Err(typed_schema_error("`ops` must not be empty"));
    }
    let mut operations = Vec::new();
    for row in rows {
        let row = row
            .as_array()
            .filter(|value| value.len() == 3)
            .ok_or_else(|| typed_schema_error("each operation must be a three-item array"))?;
        let kind = row[0]
            .as_str()
            .ok_or_else(|| typed_schema_error("operation kind must be a string"))?;
        let op = match kind {
            "body" => PatchOperationKind::ReplaceFunctionBody,
            "expr" => PatchOperationKind::ReplaceExpression,
            _ => {
                return Err(typed_schema_error(format!(
                    "unsupported operation `{kind}`"
                )))
            }
        };
        let target = row[1]
            .as_str()
            .filter(|value| !value.is_empty())
            .ok_or_else(|| typed_schema_error("operation target must be a non-empty string"))?;
        let replacement = row[2]
            .as_str()
            .ok_or_else(|| typed_schema_error("operation replacement must be a string"))?;
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

#[must_use]
pub fn compact_typed_edit(patch: &PatchDocument) -> String {
    let operations = patch
        .operations
        .iter()
        .map(|operation| {
            json!([
                match operation.op {
                    PatchOperationKind::ReplaceFunctionBody => "body",
                    PatchOperationKind::ReplaceExpression => "expr",
                },
                operation.target,
                operation.replacement,
            ])
        })
        .collect::<Vec<_>>();
    serde_json::to_string(&json!({"v": 1, "h": patch.base_hash, "cap": [], "ops": operations}))
        .unwrap_or_default()
}

#[must_use]
pub fn expand_typed_edit(edit: &TypedEditDocument) -> String {
    let patch = to_patch(edit);
    let operations = patch
        .operations
        .iter()
        .map(|operation| {
            json!({
                "op": match operation.op {
                    PatchOperationKind::ReplaceFunctionBody => "replace_function_body",
                    PatchOperationKind::ReplaceExpression => "replace_expression",
                },
                "target": operation.target,
                "replacement": operation.replacement,
            })
        })
        .collect::<Vec<_>>();
    serde_json::to_string(&json!({
        "schema_version": 1,
        "base_hash": patch.base_hash,
        "operations": operations,
    }))
    .unwrap_or_default()
}

/// Validates a typed edit without writing source.
///
/// # Errors
///
/// Returns a minimal repair context for stale, invalid, or capability-violating edits.
#[allow(clippy::result_large_err)]
pub fn validate_typed_edit(
    module: &SemanticModule,
    edit: &TypedEditDocument,
) -> Result<PatchOutcome, RepairContext> {
    if !edit.capabilities.is_empty() {
        return Err(repair_context(
            module,
            edit,
            &AgentError::new(
                "A0010",
                "source module declares no editable capabilities",
                None,
            ),
        ));
    }
    validate_patch(module, &to_patch(edit)).map_err(|error| repair_context(module, edit, &error))
}

/// Applies the same checked semantics as validation; callers decide whether to write the result.
///
/// # Errors
///
/// Returns the same repair context as [`validate_typed_edit`].
#[allow(clippy::result_large_err)]
pub fn apply_typed_edit(
    module: &SemanticModule,
    edit: &TypedEditDocument,
) -> Result<PatchOutcome, RepairContext> {
    if !edit.capabilities.is_empty() {
        return validate_typed_edit(module, edit);
    }
    apply_patch(module, &to_patch(edit)).map_err(|error| repair_context(module, edit, &error))
}

#[must_use]
pub fn repair_context(
    module: &SemanticModule,
    edit: &TypedEditDocument,
    error: &AgentError,
) -> RepairContext {
    let operation = error
        .target
        .as_ref()
        .and_then(|target| {
            edit.operations
                .iter()
                .position(|operation| &operation.target == target)
        })
        .or_else(|| (edit.operations.len() == 1).then_some(0));
    let target = error
        .target
        .clone()
        .or_else(|| (edit.operations.len() == 1).then(|| edit.operations[0].target.clone()));
    let owner = target.as_deref().and_then(|value| {
        value.strip_prefix("expr:").map_or_else(
            || value.starts_with("sym:fn:").then_some(value),
            |expression| expression.split('/').next(),
        )
    });
    let available_values = owner.map_or_else(Vec::new, |owner| {
        module
            .symbols
            .iter()
            .filter(|value| {
                value.id.starts_with(&format!("{owner}/param:"))
                    || value.id.starts_with(&format!("{owner}/body/let:"))
            })
            .map(|value| (value.id.clone(), value.ty.clone()))
            .collect()
    });
    RepairContext {
        code: error.code,
        operation,
        target,
        expected_type: error.expected_type.clone(),
        actual_type: error.actual_type.clone(),
        available_values,
        allowed_operations: vec!["body", "expr"],
        current_hash: module.content_hash.clone(),
        retryable: !matches!(error.code, "A0010"),
    }
}

fn to_patch(edit: &TypedEditDocument) -> PatchDocument {
    PatchDocument {
        schema_version: 1,
        base_hash: edit.base_hash.clone(),
        operations: edit.operations.clone(),
    }
}

fn require_keys(object: &Map<String, Value>, expected: &[&str]) -> Result<(), AgentError> {
    if let Some(key) = expected.iter().find(|key| !object.contains_key(**key)) {
        return Err(typed_schema_error(format!("missing `{key}`")));
    }
    if let Some(key) = object.keys().find(|key| !expected.contains(&key.as_str())) {
        return Err(typed_schema_error(format!("unknown field `{key}`")));
    }
    Ok(())
}

fn typed_schema_error(message: impl Into<String>) -> AgentError {
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

fn collect_type_names(text: &str, names: &mut BTreeSet<String>) {
    for value in
        text.split(|character: char| !character.is_ascii_alphanumeric() && character != '_')
    {
        if value.chars().next().is_some_and(char::is_uppercase) {
            names.insert(value.to_owned());
        }
    }
}

/// Parses a legacy patch and returns its compact equivalent.
///
/// # Errors
///
/// Returns the legacy schema error when the patch is invalid.
pub fn compact_legacy_patch(source: &str) -> Result<String, AgentError> {
    parse_patch(source).map(|patch| compact_typed_edit(&patch))
}
