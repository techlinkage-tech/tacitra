use crate::hir::{
    CallTarget, HirBinding, HirBlock, HirExpr, HirExprKind, HirFunction, HirMatchArm, HirParameter,
    HirProgram, RecordDef, SymbolId, Type, UnionDef, VariantDef,
};
use std::collections::{BTreeMap, BTreeSet};
use tacitra_syntax::{
    BinaryOp, Block, Diagnostic, Expr, ExprKind, Item, MatchArm, Program, Span, TypeRef,
    TypeRefKind, UnaryOp,
};

#[derive(Clone, Debug)]
pub struct Analysis {
    pub program: Option<HirProgram>,
    pub diagnostics: Vec<Diagnostic>,
}

#[must_use]
pub fn analyze(program: &Program) -> Analysis {
    Checker::new().analyze(program)
}

#[derive(Clone)]
struct Binding {
    id: SymbolId,
    ty: Type,
    entity: Entity,
}

#[derive(Clone)]
enum Entity {
    Value,
    Function,
    Variant(Constructor),
}

#[derive(Clone)]
struct Constructor {
    union_name: String,
    variant: String,
    payload: Option<Type>,
}

struct Checker {
    next_id: u32,
    type_names: BTreeMap<String, Type>,
    records: BTreeMap<String, RecordDef>,
    unions: BTreeMap<String, UnionDef>,
    globals: BTreeMap<String, Binding>,
    scopes: Vec<BTreeMap<String, Binding>>,
    diagnostics: Vec<Diagnostic>,
}

impl Checker {
    fn new() -> Self {
        Self {
            next_id: 0,
            type_names: BTreeMap::new(),
            records: BTreeMap::new(),
            unions: BTreeMap::new(),
            globals: BTreeMap::new(),
            scopes: Vec::new(),
            diagnostics: Vec::new(),
        }
    }

    #[allow(clippy::too_many_lines)]
    fn analyze(mut self, program: &Program) -> Analysis {
        self.collect_type_names(program);
        self.build_type_definitions(program);
        self.collect_value_declarations(program);
        let mut globals = Vec::new();
        for item in &program.items {
            if let Item::Let(binding) = item {
                let value = self.check_expr(&binding.value, None);
                let id = self.allocate();
                self.declare_global(
                    &binding.name,
                    Binding {
                        id,
                        ty: value.ty.clone(),
                        entity: Entity::Value,
                    },
                    binding.span,
                );
                globals.push(HirBinding {
                    id,
                    name: binding.name.clone(),
                    value,
                    span: binding.span,
                });
            }
        }
        let mut functions = BTreeMap::new();
        let mut main = None;
        for item in &program.items {
            if let Item::Function(function) = item {
                let Some(signature) = self.globals.get(&function.name).cloned() else {
                    continue;
                };
                if !matches!(signature.entity, Entity::Function) {
                    continue;
                }
                let Type::Function(parameter_types, result_type) = signature.ty.clone() else {
                    continue;
                };
                self.scopes.push(BTreeMap::new());
                let mut parameters = Vec::new();
                for (parameter, ty) in function.parameters.iter().zip(parameter_types) {
                    let id = self.allocate();
                    self.declare_local(
                        &parameter.name,
                        Binding {
                            id,
                            ty: ty.clone(),
                            entity: Entity::Value,
                        },
                        parameter.span,
                    );
                    parameters.push(HirParameter {
                        id,
                        name: parameter.name.clone(),
                        ty,
                        span: parameter.span,
                    });
                }
                let body = self.check_block(&function.body, Some(&result_type));
                self.scopes.pop();
                if function.name == "main" {
                    if parameters.is_empty() {
                        main = Some(signature.id);
                    } else {
                        self.diagnostics.push(Diagnostic::typed(
                            "T0016",
                            "`main` must have no parameters",
                            function.span,
                            "fn()",
                            signature.ty.to_string(),
                        ));
                    }
                }
                functions.insert(
                    signature.id,
                    HirFunction {
                        id: signature.id,
                        name: function.name.clone(),
                        parameters,
                        return_type: (*result_type).clone(),
                        body,
                        span: function.span,
                    },
                );
            }
        }
        self.diagnostics.sort_by(|left, right| {
            (left.span.start.byte, left.code, left.message.as_str()).cmp(&(
                right.span.start.byte,
                right.code,
                right.message.as_str(),
            ))
        });
        let hir = HirProgram {
            records: self.records,
            unions: self.unions,
            functions,
            globals,
            main,
        };
        Analysis {
            program: self.diagnostics.is_empty().then_some(hir),
            diagnostics: self.diagnostics,
        }
    }

    fn collect_type_names(&mut self, program: &Program) {
        for item in &program.items {
            let (name, ty, span) = match item {
                Item::Record(value) => (&value.name, Type::Record(value.name.clone()), value.span),
                Item::Union(value) => (&value.name, Type::Union(value.name.clone()), value.span),
                _ => continue,
            };
            if matches!(
                name.as_str(),
                "Int" | "Bool" | "String" | "Unit" | "Option" | "Result"
            ) || self.type_names.contains_key(name)
            {
                self.duplicate(name, span);
            } else {
                self.type_names.insert(name.clone(), ty);
            }
        }
    }

    fn build_type_definitions(&mut self, program: &Program) {
        for item in &program.items {
            match item {
                Item::Record(record)
                    if self.type_names.get(&record.name)
                        == Some(&Type::Record(record.name.clone())) =>
                {
                    let mut seen = BTreeSet::new();
                    let mut fields = Vec::new();
                    for field in &record.fields {
                        if seen.insert(field.name.clone()) {
                            fields.push((field.name.clone(), self.resolve_type(&field.ty)));
                        } else {
                            self.duplicate(&field.name, field.span);
                        }
                    }
                    self.records
                        .entry(record.name.clone())
                        .or_insert(RecordDef {
                            fields,
                            span: record.span,
                        });
                }
                Item::Union(union)
                    if self.type_names.get(&union.name)
                        == Some(&Type::Union(union.name.clone())) =>
                {
                    let mut seen = BTreeSet::new();
                    let mut variants = Vec::new();
                    for variant in &union.variants {
                        if seen.insert(variant.name.clone()) {
                            variants.push(VariantDef {
                                name: variant.name.clone(),
                                payload: variant.payload.as_ref().map(|ty| self.resolve_type(ty)),
                            });
                        } else {
                            self.duplicate(&variant.name, variant.span);
                        }
                    }
                    self.unions.entry(union.name.clone()).or_insert(UnionDef {
                        variants,
                        span: union.span,
                    });
                }
                _ => {}
            }
        }
    }

    fn collect_value_declarations(&mut self, program: &Program) {
        for item in &program.items {
            match item {
                Item::Function(function) => {
                    let parameters = function
                        .parameters
                        .iter()
                        .map(|parameter| self.resolve_type(&parameter.ty))
                        .collect();
                    let result = self.resolve_type(&function.return_type);
                    let id = self.allocate();
                    self.declare_global(
                        &function.name,
                        Binding {
                            id,
                            ty: Type::Function(parameters, Box::new(result)),
                            entity: Entity::Function,
                        },
                        function.span,
                    );
                }
                Item::Union(union) => {
                    let Some(definition) = self.unions.get(&union.name).cloned() else {
                        continue;
                    };
                    for (syntax, variant) in union.variants.iter().zip(definition.variants) {
                        let id = self.allocate();
                        let parameters = variant.payload.clone().into_iter().collect();
                        let constructor = Constructor {
                            union_name: union.name.clone(),
                            variant: variant.name.clone(),
                            payload: variant.payload,
                        };
                        self.declare_global(
                            &variant.name,
                            Binding {
                                id,
                                ty: Type::Function(
                                    parameters,
                                    Box::new(Type::Union(union.name.clone())),
                                ),
                                entity: Entity::Variant(constructor),
                            },
                            syntax.span,
                        );
                    }
                }
                _ => {}
            }
        }
    }

    fn resolve_type(&mut self, reference: &TypeRef) -> Type {
        match &reference.kind {
            TypeRefKind::Named(name) => match name.as_str() {
                "Int" => Type::Int,
                "Bool" => Type::Bool,
                "String" => Type::String,
                "Unit" => Type::Unit,
                _ => self.type_names.get(name).cloned().unwrap_or_else(|| {
                    self.diagnostics.push(Diagnostic::error(
                        "N0003",
                        format!("undefined type `{name}`"),
                        reference.span,
                    ));
                    Type::Error
                }),
            },
            TypeRefKind::Option(inner) => Type::Option(Box::new(self.resolve_type(inner))),
            TypeRefKind::Result(ok, error) => Type::Result(
                Box::new(self.resolve_type(ok)),
                Box::new(self.resolve_type(error)),
            ),
        }
    }

    fn check_block(&mut self, block: &Block, expected: Option<&Type>) -> HirBlock {
        self.scopes.push(BTreeMap::new());
        let mut bindings = Vec::new();
        for binding in &block.bindings {
            let value = self.check_expr(&binding.value, None);
            let id = self.allocate();
            self.declare_local(
                &binding.name,
                Binding {
                    id,
                    ty: value.ty.clone(),
                    entity: Entity::Value,
                },
                binding.span,
            );
            bindings.push(HirBinding {
                id,
                name: binding.name.clone(),
                value,
                span: binding.span,
            });
        }
        let result = Box::new(self.check_expr(&block.result, expected));
        self.scopes.pop();
        HirBlock { bindings, result }
    }

    fn check_expr(&mut self, expression: &Expr, expected: Option<&Type>) -> HirExpr {
        let hir = self.infer_expr(expression, expected);
        if let Some(expected) = expected {
            if hir.ty != *expected && hir.ty != Type::Error && *expected != Type::Error {
                self.diagnostics.push(Diagnostic::typed(
                    "T0001",
                    "type mismatch",
                    expression.span,
                    expected.to_string(),
                    hir.ty.to_string(),
                ));
            }
        }
        hir
    }

    fn infer_expr(&mut self, expression: &Expr, expected: Option<&Type>) -> HirExpr {
        let (kind, ty) = match &expression.kind {
            ExprKind::Integer(value) => (HirExprKind::Integer(*value), Type::Int),
            ExprKind::Boolean(value) => (HirExprKind::Boolean(*value), Type::Bool),
            ExprKind::String(value) => (HirExprKind::String(value.clone()), Type::String),
            ExprKind::Unit => (HirExprKind::Unit, Type::Unit),
            ExprKind::Name(name) => return self.check_name(name, expression.span),
            ExprKind::Unary { op, operand } => {
                let wanted = match op {
                    UnaryOp::Not => Type::Bool,
                    UnaryOp::Negate => Type::Int,
                };
                let operand = Box::new(self.check_expr(operand, Some(&wanted)));
                (HirExprKind::Unary { op: *op, operand }, wanted)
            }
            ExprKind::Binary { left, op, right } => {
                return self.check_binary(expression.span, left, *op, right)
            }
            ExprKind::Call { callee, arguments } => {
                return self.check_call(expression.span, callee, arguments, expected)
            }
            ExprKind::Field { target, name } => {
                return self.check_field(expression.span, target, name)
            }
            ExprKind::If {
                condition,
                then_block,
                else_block,
            } => {
                let condition = Box::new(self.check_expr(condition, Some(&Type::Bool)));
                let then_block = self.check_block(then_block, expected);
                let branch_type = expected
                    .cloned()
                    .unwrap_or_else(|| then_block.result.ty.clone());
                let else_block = self.check_block(else_block, Some(&branch_type));
                (
                    HirExprKind::If {
                        condition,
                        then_block,
                        else_block,
                    },
                    branch_type,
                )
            }
            ExprKind::Record { name, fields } => {
                return self.check_record(expression.span, name, fields)
            }
            ExprKind::Match { target, arms } => {
                return self.check_match(expression.span, target, arms, expected)
            }
        };
        HirExpr {
            kind,
            ty,
            span: expression.span,
        }
    }

    fn check_name(&mut self, name: &str, span: Span) -> HirExpr {
        if let Some(binding) = self.lookup(name).cloned() {
            if matches!(binding.entity, Entity::Variant(_)) {
                self.diagnostics.push(Diagnostic::error(
                    "T0002",
                    format!("constructor `{name}` must be called"),
                    span,
                ));
                return self.error_expr(span);
            }
            HirExpr {
                kind: HirExprKind::Name(binding.id),
                ty: binding.ty,
                span,
            }
        } else {
            self.diagnostics.push(Diagnostic::error(
                "N0002",
                format!("undefined name `{name}`"),
                span,
            ));
            self.error_expr(span)
        }
    }

    fn check_binary(&mut self, span: Span, left: &Expr, op: BinaryOp, right: &Expr) -> HirExpr {
        let (operand, result) = match op {
            BinaryOp::Add | BinaryOp::Subtract | BinaryOp::Multiply | BinaryOp::Divide => {
                (Type::Int, Type::Int)
            }
            BinaryOp::Less | BinaryOp::LessEqual | BinaryOp::Greater | BinaryOp::GreaterEqual => {
                (Type::Int, Type::Bool)
            }
            BinaryOp::And | BinaryOp::Or => (Type::Bool, Type::Bool),
            BinaryOp::Equal | BinaryOp::NotEqual => {
                let left = Box::new(self.check_expr(left, None));
                let right = Box::new(self.check_expr(right, Some(&left.ty)));
                if matches!(left.ty, Type::Function(_, _)) {
                    self.diagnostics.push(Diagnostic::typed(
                        "T0005",
                        "functions cannot be compared",
                        span,
                        "comparable value",
                        left.ty.to_string(),
                    ));
                }
                return HirExpr {
                    kind: HirExprKind::Binary { left, op, right },
                    ty: Type::Bool,
                    span,
                };
            }
        };
        let left = Box::new(self.check_expr(left, Some(&operand)));
        let right = Box::new(self.check_expr(right, Some(&operand)));
        HirExpr {
            kind: HirExprKind::Binary { left, op, right },
            ty: result,
            span,
        }
    }

    fn check_call(
        &mut self,
        span: Span,
        callee: &Expr,
        arguments: &[Expr],
        expected: Option<&Type>,
    ) -> HirExpr {
        let ExprKind::Name(name) = &callee.kind else {
            self.diagnostics.push(Diagnostic::error(
                "T0002",
                "call target must be a named function or constructor",
                callee.span,
            ));
            return self.error_expr(span);
        };
        if matches!(name.as_str(), "Some" | "None" | "Ok" | "Err") {
            return self.check_builtin_call(span, name, arguments, expected);
        }
        let Some(binding) = self.lookup(name).cloned() else {
            self.diagnostics.push(Diagnostic::error(
                "N0002",
                format!("undefined name `{name}`"),
                callee.span,
            ));
            return self.error_expr(span);
        };
        let (target, parameter_types, result) = match (binding.entity, binding.ty) {
            (Entity::Function, Type::Function(parameters, result)) => {
                (CallTarget::Function(binding.id), parameters, *result)
            }
            (Entity::Variant(constructor), Type::Function(parameters, result)) => (
                CallTarget::Variant {
                    union_name: constructor.union_name,
                    variant: constructor.variant,
                    has_payload: constructor.payload.is_some(),
                },
                parameters,
                *result,
            ),
            (_, actual) => {
                self.diagnostics.push(Diagnostic::typed(
                    "T0002",
                    format!("`{name}` is not callable"),
                    callee.span,
                    "function",
                    actual.to_string(),
                ));
                return self.error_expr(span);
            }
        };
        if arguments.len() != parameter_types.len() {
            self.diagnostics.push(Diagnostic::typed(
                "T0003",
                format!("wrong number of arguments to `{name}`"),
                span,
                parameter_types.len().to_string(),
                arguments.len().to_string(),
            ));
        }
        let arguments = arguments
            .iter()
            .enumerate()
            .map(|(index, argument)| self.check_expr(argument, parameter_types.get(index)))
            .collect();
        HirExpr {
            kind: HirExprKind::Call { target, arguments },
            ty: result,
            span,
        }
    }

    fn check_builtin_call(
        &mut self,
        span: Span,
        name: &str,
        arguments: &[Expr],
        expected: Option<&Type>,
    ) -> HirExpr {
        let arity = usize::from(name != "None");
        if arguments.len() != arity {
            self.diagnostics.push(Diagnostic::typed(
                "T0003",
                format!("wrong number of arguments to `{name}`"),
                span,
                arity.to_string(),
                arguments.len().to_string(),
            ));
        }
        match name {
            "Some" => {
                let inner_expected = match expected {
                    Some(Type::Option(inner)) => Some(inner.as_ref()),
                    _ => None,
                };
                let arguments = arguments
                    .iter()
                    .map(|value| self.check_expr(value, inner_expected))
                    .collect::<Vec<_>>();
                let inner = arguments
                    .first()
                    .map_or(Type::Error, |value| value.ty.clone());
                HirExpr {
                    kind: HirExprKind::Call {
                        target: CallTarget::Some,
                        arguments,
                    },
                    ty: Type::Option(Box::new(inner)),
                    span,
                }
            }
            "None" => {
                if let Some(Type::Option(inner)) = expected {
                    HirExpr {
                        kind: HirExprKind::Call {
                            target: CallTarget::None,
                            arguments: Vec::new(),
                        },
                        ty: Type::Option(inner.clone()),
                        span,
                    }
                } else {
                    self.ambiguous_constructor(name, span)
                }
            }
            "Ok" | "Err" => {
                let expected_parts = match expected {
                    Some(Type::Result(ok, error)) => Some((ok.as_ref(), error.as_ref())),
                    _ => None,
                };
                let payload_expected =
                    expected_parts.map(|(ok, error)| if name == "Ok" { ok } else { error });
                let arguments = arguments
                    .iter()
                    .map(|value| self.check_expr(value, payload_expected))
                    .collect::<Vec<_>>();
                let payload = arguments
                    .first()
                    .map_or(Type::Error, |value| value.ty.clone());
                let ty = if let Some((ok, error)) = expected_parts {
                    Type::Result(Box::new(ok.clone()), Box::new(error.clone()))
                } else if name == "Ok" {
                    Type::Result(Box::new(payload), Box::new(Type::Error))
                } else {
                    Type::Result(Box::new(Type::Error), Box::new(payload))
                };
                if expected_parts.is_none() {
                    return self.ambiguous_constructor(name, span);
                }
                let target = if name == "Ok" {
                    CallTarget::Ok
                } else {
                    CallTarget::Err
                };
                HirExpr {
                    kind: HirExprKind::Call { target, arguments },
                    ty,
                    span,
                }
            }
            _ => unreachable!(),
        }
    }

    fn ambiguous_constructor(&mut self, name: &str, span: Span) -> HirExpr {
        self.diagnostics.push(Diagnostic::error(
            "T0015",
            format!("constructor `{name}` needs an expected return type"),
            span,
        ));
        self.error_expr(span)
    }

    fn check_field(&mut self, span: Span, target: &Expr, name: &str) -> HirExpr {
        let target = Box::new(self.check_expr(target, None));
        let Type::Record(record_name) = &target.ty else {
            if target.ty != Type::Error {
                self.diagnostics.push(Diagnostic::typed(
                    "T0010",
                    "field access requires a record",
                    span,
                    "record",
                    target.ty.to_string(),
                ));
            }
            return self.error_expr(span);
        };
        let ty = self.records.get(record_name).and_then(|record| {
            record
                .fields
                .iter()
                .find(|(field, _)| field == name)
                .map(|(_, ty)| ty.clone())
        });
        if let Some(ty) = ty {
            HirExpr {
                kind: HirExprKind::Field {
                    target,
                    name: name.to_owned(),
                },
                ty,
                span,
            }
        } else {
            self.diagnostics.push(Diagnostic::error(
                "T0008",
                format!("record `{record_name}` has no field `{name}`"),
                span,
            ));
            self.error_expr(span)
        }
    }

    fn check_record(
        &mut self,
        span: Span,
        name: &str,
        fields: &[tacitra_syntax::FieldValue],
    ) -> HirExpr {
        let Some(definition) = self.records.get(name).cloned() else {
            self.diagnostics.push(Diagnostic::error(
                "N0003",
                format!("undefined record type `{name}`"),
                span,
            ));
            return self.error_expr(span);
        };
        let declared = definition
            .fields
            .iter()
            .cloned()
            .collect::<BTreeMap<_, _>>();
        let mut seen = BTreeSet::new();
        let mut values = Vec::new();
        for field in fields {
            if !seen.insert(field.name.clone()) {
                self.duplicate(&field.name, field.span);
            }
            if let Some(ty) = declared.get(&field.name) {
                values.push((field.name.clone(), self.check_expr(&field.value, Some(ty))));
            } else {
                self.diagnostics.push(Diagnostic::error(
                    "T0008",
                    format!("record `{name}` has no field `{}`", field.name),
                    field.span,
                ));
            }
        }
        for field in declared.keys() {
            if !seen.contains(field) {
                self.diagnostics.push(Diagnostic::error(
                    "T0009",
                    format!("missing field `{field}` for record `{name}`"),
                    span,
                ));
            }
        }
        let expected_order = definition
            .fields
            .iter()
            .map(|(field, _)| field.as_str())
            .collect::<Vec<_>>();
        let actual_order = fields
            .iter()
            .map(|field| field.name.as_str())
            .collect::<Vec<_>>();
        if expected_order.len() == actual_order.len()
            && actual_order
                .iter()
                .all(|field| declared.contains_key(*field))
            && actual_order.iter().collect::<BTreeSet<_>>().len() == actual_order.len()
            && expected_order != actual_order
        {
            self.diagnostics.push(Diagnostic::typed(
                "T0017",
                "record fields must follow declaration order",
                span,
                expected_order.join(", "),
                actual_order.join(", "),
            ));
        }
        HirExpr {
            kind: HirExprKind::Record {
                name: name.to_owned(),
                fields: values,
            },
            ty: Type::Record(name.to_owned()),
            span,
        }
    }

    #[allow(clippy::too_many_lines)]
    fn check_match(
        &mut self,
        span: Span,
        target: &Expr,
        arms: &[MatchArm],
        expected: Option<&Type>,
    ) -> HirExpr {
        let target = Box::new(self.check_expr(target, None));
        let variants = match &target.ty {
            Type::Option(inner) => vec![
                ("Some".to_owned(), Some((**inner).clone())),
                ("None".to_owned(), None),
            ],
            Type::Result(ok, error) => vec![
                ("Ok".to_owned(), Some((**ok).clone())),
                ("Err".to_owned(), Some((**error).clone())),
            ],
            Type::Union(name) => self.unions.get(name).map_or_else(Vec::new, |union| {
                union
                    .variants
                    .iter()
                    .map(|v| (v.name.clone(), v.payload.clone()))
                    .collect()
            }),
            Type::Error => Vec::new(),
            actual => {
                self.diagnostics.push(Diagnostic::typed(
                    "T0011",
                    "match requires Option, Result, or a union",
                    target.span,
                    "matchable type",
                    actual.to_string(),
                ));
                Vec::new()
            }
        };
        let variant_map = variants.iter().cloned().collect::<BTreeMap<_, _>>();
        let mut seen = BTreeSet::new();
        let mut hir_arms = Vec::new();
        let mut result_type = expected.cloned();
        for arm in arms {
            if !seen.insert(arm.variant.clone()) {
                self.diagnostics.push(Diagnostic::error(
                    "T0013",
                    format!("duplicate match arm `{}`", arm.variant),
                    arm.span,
                ));
            }
            let Some(payload) = variant_map.get(&arm.variant) else {
                self.diagnostics.push(Diagnostic::error(
                    "T0011",
                    format!(
                        "variant `{}` does not belong to `{}`",
                        arm.variant, target.ty
                    ),
                    arm.span,
                ));
                continue;
            };
            self.scopes.push(BTreeMap::new());
            let binding = match (payload, &arm.binding) {
                (Some(ty), Some(name)) => {
                    let id = self.allocate();
                    self.declare_local(
                        name,
                        Binding {
                            id,
                            ty: ty.clone(),
                            entity: Entity::Value,
                        },
                        arm.span,
                    );
                    Some(id)
                }
                (Some(_), None) => {
                    self.diagnostics.push(Diagnostic::typed(
                        "T0014",
                        "variant pattern requires a binding",
                        arm.span,
                        "payload binding",
                        "no binding",
                    ));
                    None
                }
                (None, Some(_)) => {
                    self.diagnostics.push(Diagnostic::typed(
                        "T0014",
                        "variant pattern has no payload",
                        arm.span,
                        "no binding",
                        "payload binding",
                    ));
                    None
                }
                (None, None) => None,
            };
            let value = self.check_expr(&arm.value, result_type.as_ref());
            if result_type.is_none() {
                result_type = Some(value.ty.clone());
            }
            self.scopes.pop();
            hir_arms.push(HirMatchArm {
                variant: arm.variant.clone(),
                binding,
                binding_name: arm.binding.clone(),
                value,
                span: arm.span,
            });
        }
        let missing = variants
            .iter()
            .map(|(name, _)| name)
            .filter(|name| !seen.contains(*name))
            .cloned()
            .collect::<Vec<_>>();
        if !missing.is_empty() {
            self.diagnostics.push(Diagnostic::error(
                "T0012",
                format!("non-exhaustive match; missing {}", missing.join(", ")),
                span,
            ));
        }
        let expected_order = variants
            .iter()
            .map(|(name, _)| name.as_str())
            .collect::<Vec<_>>();
        let actual_order = arms
            .iter()
            .map(|arm| arm.variant.as_str())
            .collect::<Vec<_>>();
        if missing.is_empty() && seen.len() == arms.len() && expected_order != actual_order {
            self.diagnostics.push(Diagnostic::typed(
                "T0018",
                "match arms must follow variant declaration order",
                span,
                expected_order.join(", "),
                actual_order.join(", "),
            ));
        }
        HirExpr {
            kind: HirExprKind::Match {
                target,
                arms: hir_arms,
            },
            ty: result_type.unwrap_or(Type::Error),
            span,
        }
    }

    fn lookup(&self, name: &str) -> Option<&Binding> {
        self.scopes
            .iter()
            .rev()
            .find_map(|scope| scope.get(name))
            .or_else(|| self.globals.get(name))
    }
    fn declare_global(&mut self, name: &str, binding: Binding, span: Span) {
        if self.globals.contains_key(name) || matches!(name, "Some" | "None" | "Ok" | "Err") {
            self.duplicate(name, span);
        } else {
            self.globals.insert(name.to_owned(), binding);
        }
    }
    fn declare_local(&mut self, name: &str, binding: Binding, span: Span) {
        let duplicate = self
            .scopes
            .last()
            .is_some_and(|scope| scope.contains_key(name));
        if duplicate {
            self.duplicate(name, span);
        } else if let Some(scope) = self.scopes.last_mut() {
            scope.insert(name.to_owned(), binding);
        }
    }
    fn duplicate(&mut self, name: &str, span: Span) {
        self.diagnostics.push(Diagnostic::error(
            "N0001",
            format!("duplicate definition `{name}`"),
            span,
        ));
    }
    fn allocate(&mut self) -> SymbolId {
        let id = SymbolId(self.next_id);
        self.next_id += 1;
        id
    }
    #[allow(clippy::unused_self)]
    fn error_expr(&self, span: Span) -> HirExpr {
        HirExpr {
            kind: HirExprKind::Error,
            ty: Type::Error,
            span,
        }
    }
}
