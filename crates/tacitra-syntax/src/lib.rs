mod ast;
mod diagnostic;
mod formatter;
mod lexer;
mod parser;

pub use ast::{
    BinaryOp, Block, Expr, ExprKind, FieldDecl, FieldValue, Function, Item, LetBinding, MatchArm,
    Parameter, Position, Program, RecordDecl, Span, TypeRef, TypeRefKind, UnaryOp, UnionDecl,
    VariantDecl,
};
pub use diagnostic::{Diagnostic, Severity};
pub use formatter::format_program;
pub use lexer::{lex, Token, TokenKind};
pub use parser::{parse, ParseResult};

/// Formats valid source into its canonical representation.
///
/// # Errors
///
/// Returns all lexer and parser diagnostics when the source is invalid.
pub fn format_source(source: &str) -> Result<String, Vec<Diagnostic>> {
    let result = parse(source);
    if result.diagnostics.is_empty() {
        Ok(format_program(&result.program))
    } else {
        Err(result.diagnostics)
    }
}
