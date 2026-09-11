use crate::model::{span_value, AgentError, SemanticModule, SymbolInfo, TypeInfo};
use serde_json::{json, Value};

#[must_use]
pub fn module_summary(module: &SemanticModule) -> String {
    let public_symbols = module
        .symbols
        .iter()
        .filter(|symbol| symbol.public)
        .map(symbol_value)
        .collect::<Vec<_>>();
    let types = module
        .types
        .iter()
        .map(|ty| json!({ "id": ty.id, "name": ty.name, "kind": ty.kind }))
        .collect::<Vec<_>>();
    let calls = module.calls.iter().map(|call| json!({ "caller": call.caller, "callee": call.callee, "expression": call.expression })).collect::<Vec<_>>();
    serialize(&json!({
        "content_hash": module.content_hash, "module_id": "mod:root", "public_symbols": public_symbols,
        "types": types, "call_graph": calls,
        "counts": { "symbols": module.symbols.len(), "types": module.types.len(), "expressions": module.expressions.len() }
    }))
}

/// Describes one symbol without returning module source.
///
/// # Errors
///
/// Returns `A0001` for a missing selector or `A0002` for an ambiguous name.
pub fn symbol_describe(module: &SemanticModule, selector: &str) -> Result<String, AgentError> {
    let symbol = module.resolve_symbol(selector)?;
    let calls = module
        .calls
        .iter()
        .filter(|call| call.caller == symbol.id)
        .map(|call| call.callee.clone())
        .collect::<Vec<_>>();
    let expression_prefix = format!("expr:{}/", symbol.id);
    let expressions = module.expressions.iter().filter(|expression| expression.id.starts_with(&expression_prefix))
        .map(|expression| json!({ "id": expression.id, "kind": expression.kind, "span": span_value(expression.span), "type": expression.ty }))
        .collect::<Vec<_>>();
    let mut value = symbol_value(symbol);
    if let Some(object) = value.as_object_mut() {
        object.insert("calls".to_owned(), json!(calls));
        object.insert("content_hash".to_owned(), json!(module.content_hash));
        object.insert("expressions".to_owned(), json!(expressions));
    }
    Ok(serialize(&value))
}

/// Returns the minimum typed context needed for a focused function edit.
///
/// # Errors
///
/// Returns `A0001`/`A0002` for selection failures and `A0007` for a non-function symbol.
pub fn symbol_edit_context(module: &SemanticModule, selector: &str) -> Result<String, AgentError> {
    let symbol = module.resolve_symbol(selector)?;
    if symbol.kind != "function" {
        return Err(AgentError::new(
            "A0007",
            "edit context requires a function symbol",
            Some(symbol.id.clone()),
        ));
    }
    let prefix = format!("expr:{}/", symbol.id);
    let leaves = module
        .expressions
        .iter()
        .filter(|expression| expression.id.starts_with(&prefix))
        .filter_map(|expression| {
            expression.value.as_ref().map(|value| {
                json!({
                    "id": expression.id,
                    "kind": expression.kind,
                    "type": expression.ty,
                    "value": value,
                })
            })
        })
        .collect::<Vec<_>>();
    Ok(serialize(&json!({
        "body_target": symbol.id,
        "content_hash": module.content_hash,
        "leaves": leaves,
        "symbol_id": symbol.id,
        "type": symbol.ty,
    })))
}

/// Lists reads and calls that resolve to one semantic symbol.
///
/// # Errors
///
/// Returns `A0001` for a missing selector or `A0002` for an ambiguous name.
pub fn symbol_references(module: &SemanticModule, selector: &str) -> Result<String, AgentError> {
    let symbol = module.resolve_symbol(selector)?;
    let references = module.references.iter().filter(|reference| reference.target == symbol.id).map(|reference| json!({
        "expression": reference.expression, "from": reference.from, "kind": reference.kind, "span": span_value(reference.span)
    })).collect::<Vec<_>>();
    Ok(serialize(
        &json!({ "symbol_id": symbol.id, "references": references }),
    ))
}

/// Describes a primitive, constructed, record, or union type and its users.
///
/// # Errors
///
/// Returns `A0001` for a missing selector or `A0002` for an ambiguous name.
pub fn type_describe(module: &SemanticModule, selector: &str) -> Result<String, AgentError> {
    let ty = module.resolve_type(selector)?;
    Ok(serialize(&type_value(ty)))
}

fn symbol_value(symbol: &SymbolInfo) -> Value {
    json!({ "detail": symbol.detail, "id": symbol.id, "kind": symbol.kind, "name": symbol.name,
        "public": symbol.public, "span": span_value(symbol.span), "type": symbol.ty })
}

fn type_value(ty: &TypeInfo) -> Value {
    json!({ "detail": ty.detail, "id": ty.id, "kind": ty.kind, "name": ty.name,
        "used_by": ty.used_by.iter().collect::<Vec<_>>() })
}

fn serialize(value: &Value) -> String {
    serde_json::to_string(value).unwrap_or_default()
}
