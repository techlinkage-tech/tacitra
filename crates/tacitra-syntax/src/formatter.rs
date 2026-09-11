use crate::{BinaryOp, Block, Expr, ExprKind, Item, LetBinding, Program, TypeRef, TypeRefKind};

#[must_use]
pub fn format_program(program: &Program) -> String {
    let mut output = String::new();
    for (index, item) in program.items.iter().enumerate() {
        if index > 0 {
            output.push('\n');
        }
        match item {
            Item::Let(binding) => format_binding(&mut output, binding, 0),
            Item::Function(function) => {
                output.push_str("fn ");
                output.push_str(&function.name);
                output.push('(');
                for (index, parameter) in function.parameters.iter().enumerate() {
                    if index > 0 {
                        output.push_str(", ");
                    }
                    output.push_str(&parameter.name);
                    output.push_str(": ");
                    format_type(&mut output, &parameter.ty);
                }
                output.push_str(") -> ");
                format_type(&mut output, &function.return_type);
                output.push(' ');
                format_block(&mut output, &function.body, 0);
                output.push('\n');
            }
            Item::Record(record) => {
                output.push_str("record ");
                output.push_str(&record.name);
                output.push_str(" {\n");
                for field in &record.fields {
                    output.push_str("  ");
                    output.push_str(&field.name);
                    output.push_str(": ");
                    format_type(&mut output, &field.ty);
                    output.push_str(",\n");
                }
                output.push_str("}\n");
            }
            Item::Union(union) => {
                output.push_str("union ");
                output.push_str(&union.name);
                output.push_str(" {\n");
                for variant in &union.variants {
                    output.push_str("  ");
                    output.push_str(&variant.name);
                    if let Some(payload) = &variant.payload {
                        output.push('(');
                        format_type(&mut output, payload);
                        output.push(')');
                    }
                    output.push_str(",\n");
                }
                output.push_str("}\n");
            }
        }
    }
    output
}

fn format_type(output: &mut String, ty: &TypeRef) {
    match &ty.kind {
        TypeRefKind::Named(name) => output.push_str(name),
        TypeRefKind::Option(inner) => {
            output.push_str("Option[");
            format_type(output, inner);
            output.push(']');
        }
        TypeRefKind::Result(ok, error) => {
            output.push_str("Result[");
            format_type(output, ok);
            output.push_str(", ");
            format_type(output, error);
            output.push(']');
        }
    }
}

fn format_block(output: &mut String, block: &Block, indent: usize) {
    output.push_str("{\n");
    for binding in &block.bindings {
        format_binding(output, binding, indent + 1);
    }
    output.push_str(&"  ".repeat(indent + 1));
    format_expression(output, &block.result, 0, false, indent + 1);
    output.push('\n');
    output.push_str(&"  ".repeat(indent));
    output.push('}');
}

fn format_binding(output: &mut String, binding: &LetBinding, indent: usize) {
    output.push_str(&"  ".repeat(indent));
    output.push_str("let ");
    output.push_str(&binding.name);
    output.push_str(" = ");
    format_expression(output, &binding.value, 0, false, indent);
    output.push_str(";\n");
}

fn format_expression(
    output: &mut String,
    expression: &Expr,
    parent: u8,
    right_child: bool,
    indent: usize,
) {
    let precedence = expression_precedence(expression);
    let parentheses = precedence < parent
        || (right_child
            && precedence == parent
            && matches!(expression.kind, ExprKind::Binary { .. }));
    if parentheses {
        output.push('(');
    }
    match &expression.kind {
        ExprKind::Integer(value) => output.push_str(&value.to_string()),
        ExprKind::Boolean(value) => output.push_str(if *value { "true" } else { "false" }),
        ExprKind::String(value) => format_string(output, value),
        ExprKind::Unit => output.push_str("()"),
        ExprKind::Name(name) => output.push_str(name),
        ExprKind::Unary { op, operand } => {
            output.push_str(op.text());
            format_expression(output, operand, 7, false, indent);
        }
        ExprKind::Binary { left, op, right } => {
            let own = binary_precedence(*op);
            format_expression(output, left, own, false, indent);
            output.push(' ');
            output.push_str(op.text());
            output.push(' ');
            format_expression(output, right, own, true, indent);
        }
        ExprKind::Call { callee, arguments } => {
            format_expression(output, callee, 8, false, indent);
            output.push('(');
            for (index, argument) in arguments.iter().enumerate() {
                if index > 0 {
                    output.push_str(", ");
                }
                format_expression(output, argument, 0, false, indent);
            }
            output.push(')');
        }
        ExprKind::Field { target, name } => {
            format_expression(output, target, 8, false, indent);
            output.push('.');
            output.push_str(name);
        }
        ExprKind::If {
            condition,
            then_block,
            else_block,
        } => {
            output.push_str("if ");
            format_expression(output, condition, 0, false, indent);
            output.push(' ');
            format_block(output, then_block, indent);
            output.push_str(" else ");
            format_block(output, else_block, indent);
        }
        ExprKind::Record { name, fields } => {
            output.push_str("new ");
            output.push_str(name);
            output.push_str(" { ");
            for (index, field) in fields.iter().enumerate() {
                if index > 0 {
                    output.push_str(", ");
                }
                output.push_str(&field.name);
                output.push_str(": ");
                format_expression(output, &field.value, 0, false, indent);
            }
            output.push_str(" }");
        }
        ExprKind::Match { target, arms } => {
            output.push_str("match ");
            format_expression(output, target, 0, false, indent);
            output.push_str(" {\n");
            for arm in arms {
                output.push_str(&"  ".repeat(indent + 1));
                output.push_str(&arm.variant);
                if let Some(binding) = &arm.binding {
                    output.push('(');
                    output.push_str(binding);
                    output.push(')');
                }
                output.push_str(" => ");
                format_expression(output, &arm.value, 0, false, indent + 1);
                output.push_str(",\n");
            }
            output.push_str(&"  ".repeat(indent));
            output.push('}');
        }
    }
    if parentheses {
        output.push(')');
    }
}

fn format_string(output: &mut String, value: &str) {
    output.push('"');
    for character in value.chars() {
        match character {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            c => output.push(c),
        }
    }
    output.push('"');
}

fn expression_precedence(expression: &Expr) -> u8 {
    match expression.kind {
        ExprKind::Binary { op, .. } => binary_precedence(op),
        ExprKind::Unary { .. } => 7,
        ExprKind::Call { .. } | ExprKind::Field { .. } => 8,
        ExprKind::Integer(_)
        | ExprKind::Boolean(_)
        | ExprKind::String(_)
        | ExprKind::Unit
        | ExprKind::Name(_)
        | ExprKind::If { .. }
        | ExprKind::Record { .. }
        | ExprKind::Match { .. } => 9,
    }
}

const fn binary_precedence(operator: BinaryOp) -> u8 {
    match operator {
        BinaryOp::Or => 1,
        BinaryOp::And => 2,
        BinaryOp::Equal | BinaryOp::NotEqual => 3,
        BinaryOp::Less | BinaryOp::LessEqual | BinaryOp::Greater | BinaryOp::GreaterEqual => 4,
        BinaryOp::Add | BinaryOp::Subtract => 5,
        BinaryOp::Multiply | BinaryOp::Divide => 6,
    }
}
