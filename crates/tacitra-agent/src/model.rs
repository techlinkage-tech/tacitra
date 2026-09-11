use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::Write as _,
};
use tacitra_semantics::{
    analyze, CallTarget, HirBlock, HirExpr, HirExprKind, HirFunction, HirProgram, SymbolId, Type,
};
use tacitra_syntax::{format_program, parse, Diagnostic, Item, Span};

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AgentError {
    pub code: &'static str,
    pub message: String,
    pub target: Option<String>,
}

impl AgentError {
    #[must_use]
    pub fn new(code: &'static str, message: impl Into<String>, target: Option<String>) -> Self {
        Self {
            code,
            message: message.into(),
            target,
        }
    }

    #[must_use]
    pub fn to_json(&self) -> String {
        serde_json::to_string(
            &json!({ "code": self.code, "message": self.message, "target": self.target }),
        )
        .unwrap_or_default()
    }
}

#[derive(Clone, Debug)]
pub struct SemanticModule {
    pub(crate) source: String,
    pub(crate) canonical_source: String,
    pub(crate) ast: tacitra_syntax::Program,
    pub(crate) content_hash: String,
    pub(crate) symbols: Vec<SymbolInfo>,
    pub(crate) types: Vec<TypeInfo>,
    pub(crate) expressions: Vec<ExpressionInfo>,
    pub(crate) references: Vec<ReferenceInfo>,
    pub(crate) calls: Vec<CallInfo>,
}

#[derive(Clone, Debug)]
pub(crate) struct SymbolInfo {
    pub id: String,
    pub name: String,
    pub kind: &'static str,
    pub ty: String,
    pub span: Span,
    pub public: bool,
    pub detail: Value,
}

#[derive(Clone, Debug)]
pub(crate) struct TypeInfo {
    pub id: String,
    pub name: String,
    pub kind: &'static str,
    pub detail: Value,
    pub used_by: BTreeSet<String>,
}

#[derive(Clone, Debug)]
pub(crate) struct ExpressionInfo {
    pub id: String,
    pub kind: &'static str,
    pub ty: String,
    pub span: Span,
    pub value: Option<Value>,
}

#[derive(Clone, Debug)]
pub(crate) struct ReferenceInfo {
    pub target: String,
    pub from: String,
    pub expression: String,
    pub kind: &'static str,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub(crate) struct CallInfo {
    pub caller: String,
    pub callee: String,
    pub expression: String,
}

impl SemanticModule {
    /// Parses and checks a source module, then constructs its deterministic semantic index.
    ///
    /// # Errors
    ///
    /// Returns lexer, parser, name, or type diagnostics when the module is invalid.
    pub fn build(source: &str) -> Result<Self, Vec<Diagnostic>> {
        let parsed = parse(source);
        if !parsed.diagnostics.is_empty() {
            return Err(parsed.diagnostics);
        }
        let analysis = analyze(&parsed.program);
        if !analysis.diagnostics.is_empty() {
            return Err(analysis.diagnostics);
        }
        let canonical_source = format_program(&parsed.program);
        let content_hash = hash_text(&canonical_source);
        let Some(hir) = analysis.program else {
            return Err(vec![Diagnostic::error(
                "R0099",
                "successful analysis did not produce HIR",
                parsed.program.span,
            )]);
        };
        Ok(IndexBuilder::new(
            source.to_owned(),
            canonical_source,
            parsed.program,
            hir,
            content_hash,
        )
        .build())
    }

    #[must_use]
    pub fn content_hash(&self) -> &str {
        &self.content_hash
    }

    #[must_use]
    pub fn semantic_ids(&self) -> Vec<String> {
        let mut ids = self
            .symbols
            .iter()
            .map(|value| value.id.clone())
            .chain(self.types.iter().map(|value| value.id.clone()))
            .chain(self.expressions.iter().map(|value| value.id.clone()))
            .collect::<Vec<_>>();
        ids.sort();
        ids
    }

    pub(crate) fn resolve_symbol(&self, selector: &str) -> Result<&SymbolInfo, AgentError> {
        resolve(
            selector,
            &self.symbols,
            |value| &value.id,
            |value| &value.name,
        )
    }

    pub(crate) fn resolve_type(&self, selector: &str) -> Result<&TypeInfo, AgentError> {
        resolve(
            selector,
            &self.types,
            |value| &value.id,
            |value| &value.name,
        )
    }

    pub(crate) fn resolve_patch_target(&self, selector: &str) -> Result<PatchTarget, AgentError> {
        if !selector.starts_with("sym:") && !selector.starts_with("expr:") {
            let named = self
                .symbols
                .iter()
                .filter(|symbol| symbol.name == selector)
                .count();
            if named > 1 {
                return Err(AgentError::new(
                    "A0002",
                    "target is ambiguous; use a semantic ID",
                    Some(selector.to_owned()),
                ));
            }
        }
        let mut candidates = Vec::new();
        for symbol in &self.symbols {
            if symbol.kind == "function" && (symbol.id == selector || symbol.name == selector) {
                let function = self
                    .ast
                    .items
                    .iter()
                    .find_map(|item| match item {
                        Item::Function(value) if value.name == symbol.name => Some(value),
                        _ => None,
                    })
                    .expect("indexed function has syntax");
                candidates.push(PatchTarget {
                    id: symbol.id.clone(),
                    kind: PatchTargetKind::FunctionBody,
                    span: function.body.span,
                    name: symbol.name.clone(),
                });
            }
        }
        for expression in &self.expressions {
            if expression.id == selector {
                candidates.push(PatchTarget {
                    id: expression.id.clone(),
                    kind: PatchTargetKind::Expression,
                    span: expression.span,
                    name: expression.id.clone(),
                });
            }
        }
        match candidates.len() {
            0 => Err(AgentError::new(
                "A0001",
                "target does not exist",
                Some(selector.to_owned()),
            )),
            1 => Ok(candidates.remove(0)),
            _ => Err(AgentError::new(
                "A0002",
                "target is ambiguous; use a semantic ID",
                Some(selector.to_owned()),
            )),
        }
    }
}

fn resolve<'a, T>(
    selector: &str,
    values: &'a [T],
    id: impl Fn(&T) -> &String,
    name: impl Fn(&T) -> &String,
) -> Result<&'a T, AgentError> {
    let exact = values
        .iter()
        .filter(|value| id(value) == selector)
        .collect::<Vec<_>>();
    if exact.len() == 1 {
        return Ok(exact[0]);
    }
    let named = values
        .iter()
        .filter(|value| name(value) == selector)
        .collect::<Vec<_>>();
    match named.len() {
        0 => Err(AgentError::new(
            "A0001",
            "target does not exist",
            Some(selector.to_owned()),
        )),
        1 => Ok(named[0]),
        _ => Err(AgentError::new(
            "A0002",
            "target is ambiguous; use a semantic ID",
            Some(selector.to_owned()),
        )),
    }
}

#[derive(Clone, Debug)]
pub(crate) struct PatchTarget {
    pub id: String,
    pub kind: PatchTargetKind,
    pub span: Span,
    pub name: String,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PatchTargetKind {
    FunctionBody,
    Expression,
}

struct IndexBuilder {
    source: String,
    canonical_source: String,
    ast: tacitra_syntax::Program,
    hir: HirProgram,
    content_hash: String,
    symbols: Vec<SymbolInfo>,
    types: BTreeMap<String, TypeInfo>,
    expressions: Vec<ExpressionInfo>,
    references: Vec<ReferenceInfo>,
    calls: Vec<CallInfo>,
    ids: BTreeMap<SymbolId, String>,
}

impl IndexBuilder {
    fn new(
        source: String,
        canonical_source: String,
        ast: tacitra_syntax::Program,
        hir: HirProgram,
        content_hash: String,
    ) -> Self {
        Self {
            source,
            canonical_source,
            ast,
            hir,
            content_hash,
            symbols: Vec::new(),
            types: BTreeMap::new(),
            expressions: Vec::new(),
            references: Vec::new(),
            calls: Vec::new(),
            ids: BTreeMap::new(),
        }
    }

    #[allow(clippy::too_many_lines)]
    fn build(mut self) -> SemanticModule {
        self.add_builtin_types();
        for item in &self.ast.items.clone() {
            match item {
                Item::Record(record) => {
                    let id = format!("type:record:{}", record.name);
                    let fields = record
                        .fields
                        .iter()
                        .map(
                            |field| json!({ "name": field.name, "type": type_ref_text(&field.ty) }),
                        )
                        .collect::<Vec<_>>();
                    self.symbols.push(SymbolInfo {
                        id: id.clone(),
                        name: record.name.clone(),
                        kind: "record",
                        ty: record.name.clone(),
                        span: record.span,
                        public: true,
                        detail: json!({ "fields": fields }),
                    });
                    self.types.insert(
                        record.name.clone(),
                        TypeInfo {
                            id,
                            name: record.name.clone(),
                            kind: "record",
                            detail: json!({ "fields": fields }),
                            used_by: BTreeSet::new(),
                        },
                    );
                }
                Item::Union(union) => {
                    let id = format!("type:union:{}", union.name);
                    let variants = union.variants.iter().map(|variant| json!({ "name": variant.name, "payload_type": variant.payload.as_ref().map(type_ref_text) })).collect::<Vec<_>>();
                    self.symbols.push(SymbolInfo {
                        id: id.clone(),
                        name: union.name.clone(),
                        kind: "union",
                        ty: union.name.clone(),
                        span: union.span,
                        public: true,
                        detail: json!({ "variants": variants }),
                    });
                    self.types.insert(
                        union.name.clone(),
                        TypeInfo {
                            id,
                            name: union.name.clone(),
                            kind: "union",
                            detail: json!({ "variants": variants }),
                            used_by: BTreeSet::new(),
                        },
                    );
                    for variant in &union.variants {
                        self.symbols.push(SymbolInfo { id: format!("sym:variant:{}.{}", union.name, variant.name), name: variant.name.clone(), kind: "variant", ty: union.name.clone(), span: variant.span, public: true, detail: json!({ "union": union.name, "payload_type": variant.payload.as_ref().map(type_ref_text) }) });
                    }
                }
                Item::Function(function) => {
                    let hir = self
                        .hir
                        .functions
                        .values()
                        .find(|value| value.name == function.name)
                        .expect("checked function is indexed")
                        .clone();
                    let id = format!("sym:fn:{}", function.name);
                    self.ids.insert(hir.id, id.clone());
                    let parameters = hir.parameters.iter().map(|parameter| json!({ "name": parameter.name, "type": parameter.ty.to_string() })).collect::<Vec<_>>();
                    let failure = failure_type(&hir.return_type);
                    self.symbols.push(SymbolInfo { id, name: function.name.clone(), kind: "function", ty: Type::Function(hir.parameters.iter().map(|value| value.ty.clone()).collect(), Box::new(hir.return_type.clone())).to_string(), span: function.span, public: true,
                        detail: json!({ "parameters": parameters, "return_type": hir.return_type.to_string(), "failure_type": failure, "effects": [], "contracts": [] }) });
                }
                Item::Let(binding) => {
                    let hir = self
                        .hir
                        .globals
                        .iter()
                        .find(|value| value.name == binding.name)
                        .expect("checked global is indexed");
                    let id = format!("sym:global:{}", binding.name);
                    self.ids.insert(hir.id, id.clone());
                    self.symbols.push(SymbolInfo {
                        id,
                        name: binding.name.clone(),
                        kind: "global",
                        ty: hir.value.ty.to_string(),
                        span: binding.span,
                        public: true,
                        detail: json!({ "immutable": true }),
                    });
                }
            }
        }
        let functions = self.hir.functions.values().cloned().collect::<Vec<_>>();
        for function in &functions {
            let owner = format!("sym:fn:{}", function.name);
            for parameter in &function.parameters {
                let id = format!("{owner}/param:{}", parameter.name);
                self.ids.insert(parameter.id, id.clone());
                self.symbols.push(SymbolInfo {
                    id,
                    name: parameter.name.clone(),
                    kind: "parameter",
                    ty: parameter.ty.to_string(),
                    span: parameter.span,
                    public: false,
                    detail: json!({ "owner": owner }),
                });
            }
            self.collect_block_symbols(&owner, "body", &function.body);
        }
        let globals = self.hir.globals.clone();
        for binding in &globals {
            self.collect_expr_symbols(
                &format!("sym:global:{}", binding.name),
                "init",
                &binding.value,
            );
        }
        for function in &functions {
            self.collect_exprs_for_function(function);
        }
        self.collect_type_usage();
        self.symbols.sort_by(|left, right| left.id.cmp(&right.id));
        self.expressions
            .sort_by(|left, right| left.id.cmp(&right.id));
        self.references.sort_by(|left, right| {
            (
                left.target.as_str(),
                left.span.start.byte,
                left.expression.as_str(),
            )
                .cmp(&(
                    right.target.as_str(),
                    right.span.start.byte,
                    right.expression.as_str(),
                ))
        });
        self.calls.sort_by(|left, right| {
            (
                left.caller.as_str(),
                left.callee.as_str(),
                left.expression.as_str(),
            )
                .cmp(&(
                    right.caller.as_str(),
                    right.callee.as_str(),
                    right.expression.as_str(),
                ))
        });
        SemanticModule {
            source: self.source,
            canonical_source: self.canonical_source,
            ast: self.ast,
            content_hash: self.content_hash,
            symbols: self.symbols,
            types: self.types.into_values().collect(),
            expressions: self.expressions,
            references: self.references,
            calls: self.calls,
        }
    }

    fn add_builtin_types(&mut self) {
        for name in ["Bool", "Int", "Option", "Result", "String", "Unit"] {
            self.types.insert(
                name.to_owned(),
                TypeInfo {
                    id: format!("type:builtin:{name}"),
                    name: name.to_owned(),
                    kind: "builtin",
                    detail: json!({}),
                    used_by: BTreeSet::new(),
                },
            );
        }
        for (name, ty) in [
            ("Some", "fn(T) -> Option[T]"),
            ("None", "fn() -> Option[T]"),
            ("Ok", "fn(T) -> Result[T, E]"),
            ("Err", "fn(E) -> Result[T, E]"),
        ] {
            self.symbols.push(SymbolInfo {
                id: format!("sym:builtin:{name}"),
                name: name.to_owned(),
                kind: "constructor",
                ty: ty.to_owned(),
                span: Span::default(),
                public: false,
                detail: json!({ "effects": [], "contracts": [] }),
            });
        }
    }

    fn collect_block_symbols(&mut self, owner: &str, path: &str, block: &HirBlock) {
        for binding in &block.bindings {
            let id = format!("{owner}/{path}/let:{}", binding.name);
            self.ids.insert(binding.id, id.clone());
            self.symbols.push(SymbolInfo {
                id,
                name: binding.name.clone(),
                kind: "local",
                ty: binding.value.ty.to_string(),
                span: binding.span,
                public: false,
                detail: json!({ "immutable": true, "owner": owner }),
            });
            self.collect_expr_symbols(
                owner,
                &format!("{path}/let:{}/init", binding.name),
                &binding.value,
            );
        }
        self.collect_expr_symbols(owner, &format!("{path}/result"), &block.result);
    }

    fn collect_expr_symbols(&mut self, owner: &str, path: &str, expression: &HirExpr) {
        match &expression.kind {
            HirExprKind::If {
                then_block,
                else_block,
                ..
            } => {
                self.collect_block_symbols(owner, &format!("{path}/then"), then_block);
                self.collect_block_symbols(owner, &format!("{path}/else"), else_block);
            }
            HirExprKind::Match { arms, .. } => {
                for arm in arms {
                    if let (Some(id), Some(name)) = (arm.binding, &arm.binding_name) {
                        let semantic_id = format!("{owner}/{path}/arm:{}/bind:{name}", arm.variant);
                        self.ids.insert(id, semantic_id.clone());
                        self.symbols.push(SymbolInfo {
                            id: semantic_id,
                            name: name.clone(),
                            kind: "pattern",
                            ty: self
                                .pattern_binding_type(expression, &arm.variant)
                                .unwrap_or_else(|| "<error>".to_owned()),
                            span: arm.span,
                            public: false,
                            detail: json!({ "owner": owner, "variant": arm.variant }),
                        });
                    }
                    self.collect_expr_symbols(
                        owner,
                        &format!("{path}/arm:{}/value", arm.variant),
                        &arm.value,
                    );
                }
            }
            _ => {}
        }
        for (child_path, child) in expression_children(expression) {
            self.collect_expr_symbols(owner, &format!("{path}/{child_path}"), child);
        }
    }

    fn collect_exprs_for_function(&mut self, function: &HirFunction) {
        let owner = format!("sym:fn:{}", function.name);
        self.collect_block_expressions(&owner, "body", &function.body);
    }

    fn collect_block_expressions(&mut self, owner: &str, path: &str, block: &HirBlock) {
        for binding in &block.bindings {
            self.collect_expression(
                owner,
                &format!("{path}/let:{}/init", binding.name),
                &binding.value,
            );
        }
        self.collect_expression(owner, &format!("{path}/result"), &block.result);
    }

    fn collect_expression(&mut self, owner: &str, path: &str, expression: &HirExpr) {
        let id = format!("expr:{owner}/{path}");
        let value = expression_value(expression, &self.ids);
        self.expressions.push(ExpressionInfo {
            id: id.clone(),
            kind: expression_kind(expression),
            ty: expression.ty.to_string(),
            span: expression.span,
            value,
        });
        match &expression.kind {
            HirExprKind::Name(target) => {
                if let Some(target) = self.ids.get(target) {
                    self.references.push(ReferenceInfo {
                        target: target.clone(),
                        from: owner.to_owned(),
                        expression: id.clone(),
                        kind: "read",
                        span: expression.span,
                    });
                }
            }
            HirExprKind::Call { target, .. } => {
                let target_id = match target {
                    CallTarget::Function(value) => self.ids.get(value).cloned(),
                    CallTarget::Variant {
                        union_name,
                        variant,
                        ..
                    } => Some(format!("sym:variant:{union_name}.{variant}")),
                    CallTarget::Some => Some("sym:builtin:Some".to_owned()),
                    CallTarget::None => Some("sym:builtin:None".to_owned()),
                    CallTarget::Ok => Some("sym:builtin:Ok".to_owned()),
                    CallTarget::Err => Some("sym:builtin:Err".to_owned()),
                };
                if let Some(target) = target_id {
                    self.references.push(ReferenceInfo {
                        target: target.clone(),
                        from: owner.to_owned(),
                        expression: id.clone(),
                        kind: "call",
                        span: expression.span,
                    });
                    self.calls.push(CallInfo {
                        caller: owner.to_owned(),
                        callee: target,
                        expression: id.clone(),
                    });
                }
            }
            HirExprKind::If {
                then_block,
                else_block,
                ..
            } => {
                self.collect_block_expressions(owner, &format!("{path}/then"), then_block);
                self.collect_block_expressions(owner, &format!("{path}/else"), else_block);
            }
            HirExprKind::Match { arms, .. } => {
                for arm in arms {
                    self.collect_expression(
                        owner,
                        &format!("{path}/arm:{}/value", arm.variant),
                        &arm.value,
                    );
                }
            }
            _ => {}
        }
        for (child_path, child) in expression_children(expression) {
            self.collect_expression(owner, &format!("{path}/{child_path}"), child);
        }
    }

    fn collect_type_usage(&mut self) {
        for symbol in &self.symbols.clone() {
            for name in type_names_from_text(&symbol.ty) {
                self.mark_type(&name, &symbol.id);
            }
            if let Some(result) = symbol.detail.get("return_type").and_then(Value::as_str) {
                for name in type_names_from_text(result) {
                    self.mark_type(&name, &symbol.id);
                }
            }
        }
        for item in &self.ast.items.clone() {
            match item {
                Item::Record(record) => {
                    for field in &record.fields {
                        for name in type_names_from_text(&type_ref_text(&field.ty)) {
                            self.mark_type(&name, &format!("type:record:{}", record.name));
                        }
                    }
                }
                Item::Union(union) => {
                    for variant in &union.variants {
                        if let Some(payload) = &variant.payload {
                            for name in type_names_from_text(&type_ref_text(payload)) {
                                self.mark_type(&name, &format!("type:union:{}", union.name));
                            }
                        }
                    }
                }
                _ => {}
            }
        }
    }

    fn mark_type(&mut self, name: &str, owner: &str) {
        if let Some(info) = self.types.get_mut(name) {
            info.used_by.insert(owner.to_owned());
        }
    }

    fn pattern_binding_type(&self, expression: &HirExpr, variant: &str) -> Option<String> {
        let HirExprKind::Match { target, .. } = &expression.kind else {
            return None;
        };
        match (&target.ty, variant) {
            (Type::Option(inner), "Some") => Some(inner.to_string()),
            (Type::Result(ok, _), "Ok") => Some(ok.to_string()),
            (Type::Result(_, error), "Err") => Some(error.to_string()),
            (Type::Union(name), variant) => self
                .hir
                .unions
                .get(name)?
                .variants
                .iter()
                .find(|value| value.name == variant)?
                .payload
                .as_ref()
                .map(ToString::to_string),
            _ => None,
        }
    }
}

fn expression_children(expression: &HirExpr) -> Vec<(String, &HirExpr)> {
    match &expression.kind {
        HirExprKind::Unary { operand, .. } => vec![("operand".to_owned(), operand)],
        HirExprKind::Binary { left, right, .. } => {
            vec![("left".to_owned(), left), ("right".to_owned(), right)]
        }
        HirExprKind::Call { arguments, .. } => arguments
            .iter()
            .enumerate()
            .map(|(index, value)| (format!("arg:{index}"), value))
            .collect(),
        HirExprKind::Field { target, .. } | HirExprKind::Match { target, .. } => {
            vec![("target".to_owned(), target)]
        }
        HirExprKind::If { condition, .. } => vec![("condition".to_owned(), condition)],
        HirExprKind::Record { fields, .. } => fields
            .iter()
            .map(|(name, value)| (format!("field:{name}"), value))
            .collect(),
        HirExprKind::Integer(_)
        | HirExprKind::Boolean(_)
        | HirExprKind::String(_)
        | HirExprKind::Unit
        | HirExprKind::Name(_)
        | HirExprKind::Error => Vec::new(),
    }
}

fn expression_kind(expression: &HirExpr) -> &'static str {
    match expression.kind {
        HirExprKind::Integer(_) => "integer",
        HirExprKind::Boolean(_) => "boolean",
        HirExprKind::String(_) => "string",
        HirExprKind::Unit => "unit",
        HirExprKind::Name(_) => "name",
        HirExprKind::Unary { .. } => "unary",
        HirExprKind::Binary { .. } => "binary",
        HirExprKind::Call { .. } => "call",
        HirExprKind::Field { .. } => "field",
        HirExprKind::If { .. } => "if",
        HirExprKind::Record { .. } => "record",
        HirExprKind::Match { .. } => "match",
        HirExprKind::Error => "error",
    }
}

fn expression_value(expression: &HirExpr, ids: &BTreeMap<SymbolId, String>) -> Option<Value> {
    match &expression.kind {
        HirExprKind::Integer(value) => Some(json!(value)),
        HirExprKind::Boolean(value) => Some(json!(value)),
        HirExprKind::String(value) => Some(json!(value)),
        HirExprKind::Unit => Some(Value::Null),
        HirExprKind::Name(id) => ids.get(id).map(|value| json!(value)),
        _ => None,
    }
}

fn failure_type(ty: &Type) -> Option<String> {
    if let Type::Result(_, error) = ty {
        Some(error.to_string())
    } else {
        None
    }
}

fn type_ref_text(reference: &tacitra_syntax::TypeRef) -> String {
    match &reference.kind {
        tacitra_syntax::TypeRefKind::Named(name) => name.clone(),
        tacitra_syntax::TypeRefKind::Option(inner) => format!("Option[{}]", type_ref_text(inner)),
        tacitra_syntax::TypeRefKind::Result(ok, error) => {
            format!("Result[{}, {}]", type_ref_text(ok), type_ref_text(error))
        }
    }
}

fn type_names_from_text(text: &str) -> Vec<String> {
    text.split(|character: char| !character.is_ascii_alphanumeric() && character != '_')
        .filter(|part| !part.is_empty() && *part != "fn")
        .map(str::to_owned)
        .collect()
}

pub(crate) fn hash_text(text: &str) -> String {
    let digest = Sha256::digest(text.as_bytes());
    let mut hex = String::with_capacity(64);
    for byte in digest {
        let _ = write!(hex, "{byte:02x}");
    }
    format!("sha256:{hex}")
}

pub(crate) fn span_value(span: Span) -> Value {
    json!({ "start": { "byte": span.start.byte, "line": span.start.line, "column": span.start.column },
        "end": { "byte": span.end.byte, "line": span.end.line, "column": span.end.column } })
}
