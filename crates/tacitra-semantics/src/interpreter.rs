#![allow(clippy::result_large_err)]

use crate::hir::{CallTarget, HirBlock, HirExpr, HirExprKind, HirProgram, SymbolId};
use std::collections::BTreeMap;
use tacitra_syntax::{BinaryOp, Diagnostic, Span, UnaryOp};

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Value {
    Int(i64),
    Bool(bool),
    String(String),
    Unit,
    Option(Option<Box<Value>>),
    Result(Result<Box<Value>, Box<Value>>),
    Record {
        name: String,
        fields: BTreeMap<String, Value>,
    },
    Union {
        name: String,
        variant: String,
        payload: Option<Box<Value>>,
    },
    Function(SymbolId),
}

impl Value {
    #[must_use]
    pub fn type_name(&self) -> String {
        match self {
            Self::Int(_) => "Int".to_owned(),
            Self::Bool(_) => "Bool".to_owned(),
            Self::String(_) => "String".to_owned(),
            Self::Unit => "Unit".to_owned(),
            Self::Option(_) => "Option".to_owned(),
            Self::Result(_) => "Result".to_owned(),
            Self::Record { name, .. } | Self::Union { name, .. } => name.clone(),
            Self::Function(_) => "function".to_owned(),
        }
    }

    #[must_use]
    pub fn render(&self) -> String {
        match self {
            Self::Int(value) => value.to_string(),
            Self::Bool(value) => value.to_string(),
            Self::String(value) => {
                format!("\"{}\"", value.replace('\\', "\\\\").replace('"', "\\\""))
            }
            Self::Unit => "()".to_owned(),
            Self::Option(Some(value)) => format!("Some({})", value.render()),
            Self::Option(None) => "None".to_owned(),
            Self::Result(Ok(value)) => format!("Ok({})", value.render()),
            Self::Result(Err(value)) => format!("Err({})", value.render()),
            Self::Record { name, fields } => {
                let fields = fields
                    .iter()
                    .map(|(key, value)| format!("{key}: {}", value.render()))
                    .collect::<Vec<_>>()
                    .join(", ");
                format!("{name} {{ {fields} }}")
            }
            Self::Union {
                variant,
                payload: Some(value),
                ..
            } => format!("{variant}({})", value.render()),
            Self::Union {
                variant,
                payload: None,
                ..
            } => variant.clone(),
            Self::Function(_) => "<function>".to_owned(),
        }
    }

    #[must_use]
    pub fn to_json(&self) -> String {
        format!(
            "{{\"type\":{},\"value\":{}}}",
            json_string(&self.type_name()),
            value_json(self)
        )
    }
}

/// Executes the zero-argument `main` function of a checked HIR program.
///
/// # Errors
///
/// Returns a stable runtime diagnostic if `main` is absent or an operation such as division fails.
pub fn execute_main(program: &HirProgram) -> Result<Value, Diagnostic> {
    let Some(main) = program.main else {
        return Err(Diagnostic::error(
            "R0003",
            "program has no zero-argument `main` function",
            Span::default(),
        ));
    };
    let mut globals = BTreeMap::new();
    for id in program.functions.keys() {
        globals.insert(*id, Value::Function(*id));
    }
    let mut pending = program.globals.iter().collect::<Vec<_>>();
    while !pending.is_empty() {
        let mut next = Vec::new();
        let mut progressed = false;
        for binding in pending {
            match eval_expr(program, &globals, &binding.value) {
                Ok(value) => {
                    globals.insert(binding.id, value);
                    progressed = true;
                }
                Err(error)
                    if error.code == "R0099" && error.message == "missing resolved value" =>
                {
                    next.push(binding);
                }
                Err(error) => return Err(error),
            }
        }
        if !progressed {
            return Err(Diagnostic::error(
                "R0004",
                "cyclic top-level initialization",
                next[0].value.span,
            ));
        }
        pending = next;
    }
    call_function(program, &globals, main, Vec::new(), Span::default())
}

fn call_function(
    program: &HirProgram,
    globals: &BTreeMap<SymbolId, Value>,
    id: SymbolId,
    arguments: Vec<Value>,
    span: Span,
) -> Result<Value, Diagnostic> {
    let Some(function) = program.functions.get(&id) else {
        return Err(internal(span, "missing function"));
    };
    let mut environment = globals.clone();
    for (parameter, value) in function.parameters.iter().zip(arguments) {
        environment.insert(parameter.id, value);
    }
    eval_block(program, &environment, &function.body)
}

fn eval_block(
    program: &HirProgram,
    outer: &BTreeMap<SymbolId, Value>,
    block: &HirBlock,
) -> Result<Value, Diagnostic> {
    let mut environment = outer.clone();
    for binding in &block.bindings {
        let value = eval_expr(program, &environment, &binding.value)?;
        environment.insert(binding.id, value);
    }
    eval_expr(program, &environment, &block.result)
}

#[allow(clippy::too_many_lines)]
fn eval_expr(
    program: &HirProgram,
    environment: &BTreeMap<SymbolId, Value>,
    expression: &HirExpr,
) -> Result<Value, Diagnostic> {
    match &expression.kind {
        HirExprKind::Integer(value) => Ok(Value::Int(*value)),
        HirExprKind::Boolean(value) => Ok(Value::Bool(*value)),
        HirExprKind::String(value) => Ok(Value::String(value.clone())),
        HirExprKind::Unit => Ok(Value::Unit),
        HirExprKind::Name(id) => environment
            .get(id)
            .cloned()
            .ok_or_else(|| internal(expression.span, "missing resolved value")),
        HirExprKind::Unary { op, operand } => {
            let value = eval_expr(program, environment, operand)?;
            match (op, value) {
                (UnaryOp::Not, Value::Bool(value)) => Ok(Value::Bool(!value)),
                (UnaryOp::Negate, Value::Int(value)) => value
                    .checked_neg()
                    .map(Value::Int)
                    .ok_or_else(|| Diagnostic::error("R0002", "integer overflow", expression.span)),
                _ => Err(internal(
                    expression.span,
                    "invalid checked unary expression",
                )),
            }
        }
        HirExprKind::Binary {
            left,
            op: BinaryOp::And,
            right,
        } => {
            let Value::Bool(left) = eval_expr(program, environment, left)? else {
                return Err(internal(
                    expression.span,
                    "invalid checked boolean expression",
                ));
            };
            if left {
                eval_expr(program, environment, right)
            } else {
                Ok(Value::Bool(false))
            }
        }
        HirExprKind::Binary {
            left,
            op: BinaryOp::Or,
            right,
        } => {
            let Value::Bool(left) = eval_expr(program, environment, left)? else {
                return Err(internal(
                    expression.span,
                    "invalid checked boolean expression",
                ));
            };
            if left {
                Ok(Value::Bool(true))
            } else {
                eval_expr(program, environment, right)
            }
        }
        HirExprKind::Binary { left, op, right } => {
            let left = eval_expr(program, environment, left)?;
            let right = eval_expr(program, environment, right)?;
            eval_binary(*op, left, right, expression.span)
        }
        HirExprKind::Call { target, arguments } => {
            let arguments = arguments
                .iter()
                .map(|argument| eval_expr(program, environment, argument))
                .collect::<Result<Vec<_>, _>>()?;
            match target {
                CallTarget::Function(id) => {
                    call_function(program, environment, *id, arguments, expression.span)
                }
                CallTarget::Some => Ok(Value::Option(arguments.into_iter().next().map(Box::new))),
                CallTarget::None => Ok(Value::Option(None)),
                CallTarget::Ok => Ok(Value::Result(Ok(Box::new(
                    arguments
                        .into_iter()
                        .next()
                        .ok_or_else(|| internal(expression.span, "missing Ok payload"))?,
                )))),
                CallTarget::Err => Ok(Value::Result(Err(Box::new(
                    arguments
                        .into_iter()
                        .next()
                        .ok_or_else(|| internal(expression.span, "missing Err payload"))?,
                )))),
                CallTarget::Variant {
                    union_name,
                    variant,
                    has_payload,
                } => Ok(Value::Union {
                    name: union_name.clone(),
                    variant: variant.clone(),
                    payload: if *has_payload {
                        arguments.into_iter().next().map(Box::new)
                    } else {
                        None
                    },
                }),
            }
        }
        HirExprKind::Field { target, name } => {
            let Value::Record { fields, .. } = eval_expr(program, environment, target)? else {
                return Err(internal(expression.span, "invalid checked field access"));
            };
            fields
                .get(name)
                .cloned()
                .ok_or_else(|| internal(expression.span, "missing checked field"))
        }
        HirExprKind::If {
            condition,
            then_block,
            else_block,
        } => {
            let Value::Bool(condition) = eval_expr(program, environment, condition)? else {
                return Err(internal(expression.span, "invalid checked condition"));
            };
            eval_block(
                program,
                environment,
                if condition { then_block } else { else_block },
            )
        }
        HirExprKind::Record { name, fields } => {
            let fields = fields
                .iter()
                .map(|(field, value)| Ok((field.clone(), eval_expr(program, environment, value)?)))
                .collect::<Result<_, Diagnostic>>()?;
            Ok(Value::Record {
                name: name.clone(),
                fields,
            })
        }
        HirExprKind::Match { target, arms } => {
            let target = eval_expr(program, environment, target)?;
            let (variant, payload) = match target {
                Value::Option(Some(value)) => ("Some".to_owned(), Some(value)),
                Value::Option(None) => ("None".to_owned(), None),
                Value::Result(Ok(value)) => ("Ok".to_owned(), Some(value)),
                Value::Result(Err(value)) => ("Err".to_owned(), Some(value)),
                Value::Union {
                    variant, payload, ..
                } => (variant, payload),
                _ => return Err(internal(expression.span, "invalid checked match target")),
            };
            let Some(arm) = arms.iter().find(|arm| arm.variant == variant) else {
                return Err(internal(expression.span, "missing checked match arm"));
            };
            let mut arm_environment = environment.clone();
            if let (Some(id), Some(value)) = (arm.binding, payload) {
                arm_environment.insert(id, *value);
            }
            eval_expr(program, &arm_environment, &arm.value)
        }
        HirExprKind::Error => Err(internal(expression.span, "error HIR cannot execute")),
    }
}

fn eval_binary(
    operator: BinaryOp,
    left: Value,
    right: Value,
    span: Span,
) -> Result<Value, Diagnostic> {
    match (operator, left, right) {
        (BinaryOp::Equal, left, right) => Ok(Value::Bool(left == right)),
        (BinaryOp::NotEqual, left, right) => Ok(Value::Bool(left != right)),
        (BinaryOp::Add, Value::Int(a), Value::Int(b)) => checked(a.checked_add(b), span),
        (BinaryOp::Subtract, Value::Int(a), Value::Int(b)) => checked(a.checked_sub(b), span),
        (BinaryOp::Multiply, Value::Int(a), Value::Int(b)) => checked(a.checked_mul(b), span),
        (BinaryOp::Divide, Value::Int(_), Value::Int(0)) => {
            Err(Diagnostic::error("R0001", "division by zero", span))
        }
        (BinaryOp::Divide, Value::Int(a), Value::Int(b)) => checked(a.checked_div(b), span),
        (BinaryOp::Less, Value::Int(a), Value::Int(b)) => Ok(Value::Bool(a < b)),
        (BinaryOp::LessEqual, Value::Int(a), Value::Int(b)) => Ok(Value::Bool(a <= b)),
        (BinaryOp::Greater, Value::Int(a), Value::Int(b)) => Ok(Value::Bool(a > b)),
        (BinaryOp::GreaterEqual, Value::Int(a), Value::Int(b)) => Ok(Value::Bool(a >= b)),
        _ => Err(internal(span, "invalid checked binary expression")),
    }
}

fn checked(value: Option<i64>, span: Span) -> Result<Value, Diagnostic> {
    value
        .map(Value::Int)
        .ok_or_else(|| Diagnostic::error("R0002", "integer overflow", span))
}

fn internal(span: Span, message: &str) -> Diagnostic {
    Diagnostic::error("R0099", message, span)
}

fn json_string(value: &str) -> String {
    format!(
        "\"{}\"",
        value
            .replace('\\', "\\\\")
            .replace('"', "\\\"")
            .replace('\n', "\\n")
            .replace('\r', "\\r")
            .replace('\t', "\\t")
    )
}

fn value_json(value: &Value) -> String {
    match value {
        Value::Int(value) => value.to_string(),
        Value::Bool(value) => value.to_string(),
        Value::String(value) => json_string(value),
        Value::Unit | Value::Function(_) => "null".to_owned(),
        Value::Option(Some(value)) => format!("{{\"Some\":{}}}", value_json(value)),
        Value::Option(None) => "{\"None\":null}".to_owned(),
        Value::Result(Ok(value)) => format!("{{\"Ok\":{}}}", value_json(value)),
        Value::Result(Err(value)) => format!("{{\"Err\":{}}}", value_json(value)),
        Value::Record { fields, .. } => format!(
            "{{{}}}",
            fields
                .iter()
                .map(|(key, value)| format!("{}:{}", json_string(key), value_json(value)))
                .collect::<Vec<_>>()
                .join(",")
        ),
        Value::Union {
            variant, payload, ..
        } => format!(
            "{{{}:{}}}",
            json_string(variant),
            payload
                .as_ref()
                .map_or_else(|| "null".to_owned(), |value| value_json(value))
        ),
    }
}
