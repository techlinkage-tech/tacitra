use crate::diagnostic::sort_diagnostics;
use crate::{
    lex, BinaryOp, Block, Diagnostic, Expr, ExprKind, FieldDecl, FieldValue, Function, Item,
    LetBinding, MatchArm, Parameter, Program, RecordDecl, Span, Token, TokenKind, TypeRef,
    TypeRefKind, UnaryOp, UnionDecl, VariantDecl,
};

#[derive(Clone, Debug)]
pub struct ParseResult {
    pub program: Program,
    pub diagnostics: Vec<Diagnostic>,
}

#[must_use]
pub fn parse(source: &str) -> ParseResult {
    let (tokens, diagnostics) = lex(source);
    Parser {
        tokens,
        current: 0,
        diagnostics,
    }
    .parse_program()
}

struct Parser {
    tokens: Vec<Token>,
    current: usize,
    diagnostics: Vec<Diagnostic>,
}

impl Parser {
    fn parse_program(mut self) -> ParseResult {
        let start = self.current().span.start;
        let mut items = Vec::new();
        while !self.at(&TokenKind::Eof) {
            let before = self.current;
            let item = match self.current().kind {
                TokenKind::Let => self.parse_let().map(Item::Let),
                TokenKind::Fn => self.parse_function().map(Item::Function),
                TokenKind::Record => self.parse_record().map(Item::Record),
                TokenKind::Union => self.parse_union().map(Item::Union),
                _ => {
                    self.error("P0001", "expected `let`, `fn`, `record`, or `union`");
                    None
                }
            };
            let failed = item.is_none();
            if let Some(item) = item {
                items.push(item);
            }
            if self.current == before {
                self.advance();
            }
            if failed {
                self.synchronize_top_level();
            }
        }
        let end = self.current().span.end;
        sort_diagnostics(&mut self.diagnostics);
        ParseResult {
            program: Program {
                items,
                span: Span::new(start, end),
            },
            diagnostics: self.diagnostics,
        }
    }

    fn parse_let(&mut self) -> Option<LetBinding> {
        let start = self.advance().span;
        let (name, _) = self.take_identifier("P0002", "expected binding name after `let`")?;
        self.expect(
            &TokenKind::Equal,
            "P0003",
            "expected `=` after binding name",
        )?;
        let value = self.parse_expression(1)?;
        let end = self
            .expect(&TokenKind::Semicolon, "P0004", "expected `;` after binding")?
            .span;
        Some(LetBinding {
            name,
            value,
            span: start.join(end),
        })
    }

    fn parse_function(&mut self) -> Option<Function> {
        let start = self.advance().span;
        let (name, _) = self.take_identifier("P0005", "expected function name after `fn`")?;
        self.expect(
            &TokenKind::LeftParen,
            "P0006",
            "expected `(` after function name",
        )?;
        let mut parameters = Vec::new();
        if !self.at(&TokenKind::RightParen) {
            loop {
                let (parameter_name, parameter_start) =
                    self.take_identifier("P0007", "expected parameter name")?;
                self.expect(
                    &TokenKind::Colon,
                    "P0016",
                    "expected `:` after parameter name",
                )?;
                let ty = self.parse_type()?;
                let span = parameter_start.join(ty.span);
                parameters.push(Parameter {
                    name: parameter_name,
                    ty,
                    span,
                });
                if !self.take(&TokenKind::Comma) {
                    break;
                }
                if self.at(&TokenKind::RightParen) {
                    self.error("P0017", "trailing parameter comma is not allowed");
                    return None;
                }
            }
        }
        self.expect(
            &TokenKind::RightParen,
            "P0008",
            "expected `)` after parameters",
        )?;
        self.expect(
            &TokenKind::Arrow,
            "P0018",
            "expected `->` before return type",
        )?;
        let return_type = self.parse_type()?;
        let body = self.parse_block()?;
        let span = start.join(body.span);
        Some(Function {
            name,
            parameters,
            return_type,
            body,
            span,
        })
    }

    fn parse_record(&mut self) -> Option<RecordDecl> {
        let start = self.advance().span;
        let (name, _) = self.take_identifier("P0019", "expected record name")?;
        self.expect(
            &TokenKind::LeftBrace,
            "P0020",
            "expected `{` after record name",
        )?;
        let mut fields = Vec::new();
        while !self.at(&TokenKind::RightBrace) && !self.at(&TokenKind::Eof) {
            let (field_name, field_start) = self.take_identifier("P0021", "expected field name")?;
            self.expect(&TokenKind::Colon, "P0022", "expected `:` after field name")?;
            let ty = self.parse_type()?;
            let span = field_start.join(ty.span);
            self.expect(
                &TokenKind::Comma,
                "P0023",
                "expected `,` after record field",
            )?;
            fields.push(FieldDecl {
                name: field_name,
                ty,
                span,
            });
        }
        let end = self
            .expect(
                &TokenKind::RightBrace,
                "P0024",
                "expected `}` after record fields",
            )?
            .span;
        Some(RecordDecl {
            name,
            fields,
            span: start.join(end),
        })
    }

    fn parse_union(&mut self) -> Option<UnionDecl> {
        let start = self.advance().span;
        let (name, _) = self.take_identifier("P0025", "expected union name")?;
        self.expect(
            &TokenKind::LeftBrace,
            "P0026",
            "expected `{` after union name",
        )?;
        let mut variants = Vec::new();
        while !self.at(&TokenKind::RightBrace) && !self.at(&TokenKind::Eof) {
            let (variant_name, variant_start) =
                self.take_identifier("P0027", "expected variant name")?;
            let payload = if self.take(&TokenKind::LeftParen) {
                let ty = self.parse_type()?;
                self.expect(
                    &TokenKind::RightParen,
                    "P0028",
                    "expected `)` after variant payload",
                )?;
                Some(ty)
            } else {
                None
            };
            let end = self
                .expect(
                    &TokenKind::Comma,
                    "P0029",
                    "expected `,` after union variant",
                )?
                .span;
            variants.push(VariantDecl {
                name: variant_name,
                payload,
                span: variant_start.join(end),
            });
        }
        let end = self
            .expect(
                &TokenKind::RightBrace,
                "P0030",
                "expected `}` after union variants",
            )?
            .span;
        Some(UnionDecl {
            name,
            variants,
            span: start.join(end),
        })
    }

    fn parse_type(&mut self) -> Option<TypeRef> {
        let (name, start) = self.take_identifier("P0031", "expected type")?;
        if name == "Option" {
            self.expect(
                &TokenKind::LeftBracket,
                "P0032",
                "expected `[` after `Option`",
            )?;
            let inner = self.parse_type()?;
            let end = self
                .expect(
                    &TokenKind::RightBracket,
                    "P0033",
                    "expected `]` after option type",
                )?
                .span;
            Some(TypeRef {
                kind: TypeRefKind::Option(Box::new(inner)),
                span: start.join(end),
            })
        } else if name == "Result" {
            self.expect(
                &TokenKind::LeftBracket,
                "P0034",
                "expected `[` after `Result`",
            )?;
            let ok = self.parse_type()?;
            self.expect(&TokenKind::Comma, "P0035", "expected `,` in result type")?;
            let error = self.parse_type()?;
            let end = self
                .expect(
                    &TokenKind::RightBracket,
                    "P0036",
                    "expected `]` after result type",
                )?
                .span;
            Some(TypeRef {
                kind: TypeRefKind::Result(Box::new(ok), Box::new(error)),
                span: start.join(end),
            })
        } else {
            Some(TypeRef {
                kind: TypeRefKind::Named(name),
                span: start,
            })
        }
    }

    fn parse_block(&mut self) -> Option<Block> {
        let start = self
            .expect(&TokenKind::LeftBrace, "P0009", "expected `{` before block")?
            .span;
        let mut bindings = Vec::new();
        while self.at(&TokenKind::Let) {
            if let Some(binding) = self.parse_let() {
                bindings.push(binding);
            } else {
                self.synchronize_block();
            }
        }
        if self.at(&TokenKind::RightBrace) {
            self.error("P0010", "expected result expression before `}`");
            return None;
        }
        let result = Box::new(self.parse_expression(1)?);
        let end = self
            .expect(
                &TokenKind::RightBrace,
                "P0011",
                "expected `}` after block result",
            )?
            .span;
        Some(Block {
            bindings,
            result,
            span: start.join(end),
        })
    }

    fn parse_expression(&mut self, min_precedence: u8) -> Option<Expr> {
        let mut left = self.parse_unary()?;
        while let Some((operator, precedence)) = self.binary_operator() {
            if precedence < min_precedence {
                break;
            }
            self.advance();
            let right = self.parse_expression(precedence + 1)?;
            let span = left.span.join(right.span);
            left = Expr {
                kind: ExprKind::Binary {
                    left: Box::new(left),
                    op: operator,
                    right: Box::new(right),
                },
                span,
            };
        }
        Some(left)
    }

    fn parse_unary(&mut self) -> Option<Expr> {
        let operator = if self.at(&TokenKind::Bang) {
            Some(UnaryOp::Not)
        } else if self.at(&TokenKind::Minus) {
            Some(UnaryOp::Negate)
        } else {
            None
        };
        if let Some(op) = operator {
            let start = self.advance().span;
            let operand = self.parse_unary()?;
            let span = start.join(operand.span);
            return Some(Expr {
                kind: ExprKind::Unary {
                    op,
                    operand: Box::new(operand),
                },
                span,
            });
        }
        self.parse_suffix()
    }

    fn parse_suffix(&mut self) -> Option<Expr> {
        let mut expression = self.parse_primary()?;
        loop {
            if self.take(&TokenKind::LeftParen) {
                let mut arguments = Vec::new();
                if !self.at(&TokenKind::RightParen) {
                    loop {
                        arguments.push(self.parse_expression(1)?);
                        if !self.take(&TokenKind::Comma) {
                            break;
                        }
                        if self.at(&TokenKind::RightParen) {
                            self.error("P0037", "trailing argument comma is not allowed");
                            return None;
                        }
                    }
                }
                let end = self
                    .expect(
                        &TokenKind::RightParen,
                        "P0012",
                        "expected `)` after arguments",
                    )?
                    .span;
                let span = expression.span.join(end);
                expression = Expr {
                    kind: ExprKind::Call {
                        callee: Box::new(expression),
                        arguments,
                    },
                    span,
                };
            } else if self.take(&TokenKind::Dot) {
                let (name, end) = self.take_identifier("P0038", "expected field name after `.`")?;
                let span = expression.span.join(end);
                expression = Expr {
                    kind: ExprKind::Field {
                        target: Box::new(expression),
                        name,
                    },
                    span,
                };
            } else {
                break;
            }
        }
        Some(expression)
    }

    fn parse_primary(&mut self) -> Option<Expr> {
        if self.at(&TokenKind::If) {
            return self.parse_if();
        }
        if self.at(&TokenKind::Match) {
            return self.parse_match();
        }
        if self.at(&TokenKind::New) {
            return self.parse_record_value();
        }
        let token = self.advance().clone();
        let kind = match token.kind {
            TokenKind::Integer(text) => {
                if let Ok(value) = text.parse::<i64>() {
                    ExprKind::Integer(value)
                } else {
                    self.diagnostics.push(Diagnostic::error(
                        "P0013",
                        "integer is outside the supported 64-bit range",
                        token.span,
                    ));
                    return None;
                }
            }
            TokenKind::True => ExprKind::Boolean(true),
            TokenKind::False => ExprKind::Boolean(false),
            TokenKind::String(value) => ExprKind::String(value),
            TokenKind::Identifier(name) => ExprKind::Name(name),
            TokenKind::LeftParen => {
                if self.at(&TokenKind::RightParen) {
                    let end = self.advance().span;
                    return Some(Expr {
                        kind: ExprKind::Unit,
                        span: token.span.join(end),
                    });
                }
                let mut expression = self.parse_expression(1)?;
                let end = self
                    .expect(
                        &TokenKind::RightParen,
                        "P0014",
                        "expected `)` after grouped expression",
                    )?
                    .span;
                expression.span = token.span.join(end);
                return Some(expression);
            }
            _ => {
                self.diagnostics.push(Diagnostic::error(
                    "P0015",
                    "expected expression",
                    token.span,
                ));
                return None;
            }
        };
        Some(Expr {
            kind,
            span: token.span,
        })
    }

    fn parse_if(&mut self) -> Option<Expr> {
        let start = self.advance().span;
        let condition = Box::new(self.parse_expression(1)?);
        let then_block = self.parse_block()?;
        self.expect(&TokenKind::Else, "P0039", "expected `else` after if branch")?;
        let else_block = self.parse_block()?;
        let span = start.join(else_block.span);
        Some(Expr {
            kind: ExprKind::If {
                condition,
                then_block,
                else_block,
            },
            span,
        })
    }

    fn parse_record_value(&mut self) -> Option<Expr> {
        let start = self.advance().span;
        let (name, _) = self.take_identifier("P0040", "expected record type after `new`")?;
        self.expect(
            &TokenKind::LeftBrace,
            "P0041",
            "expected `{` after record type",
        )?;
        let mut fields = Vec::new();
        if !self.at(&TokenKind::RightBrace) {
            loop {
                let (field_name, field_start) =
                    self.take_identifier("P0042", "expected initialized field name")?;
                self.expect(
                    &TokenKind::Colon,
                    "P0043",
                    "expected `:` after initialized field name",
                )?;
                let value = self.parse_expression(1)?;
                let span = field_start.join(value.span);
                fields.push(FieldValue {
                    name: field_name,
                    value,
                    span,
                });
                if !self.take(&TokenKind::Comma) {
                    break;
                }
                if self.at(&TokenKind::RightBrace) {
                    self.error("P0044", "trailing record value comma is not allowed");
                    return None;
                }
            }
        }
        let end = self
            .expect(
                &TokenKind::RightBrace,
                "P0045",
                "expected `}` after record value",
            )?
            .span;
        Some(Expr {
            kind: ExprKind::Record { name, fields },
            span: start.join(end),
        })
    }

    fn parse_match(&mut self) -> Option<Expr> {
        let start = self.advance().span;
        let target = Box::new(self.parse_expression(1)?);
        self.expect(
            &TokenKind::LeftBrace,
            "P0046",
            "expected `{` before match arms",
        )?;
        let mut arms = Vec::new();
        while !self.at(&TokenKind::RightBrace) && !self.at(&TokenKind::Eof) {
            let (variant, arm_start) = self.take_identifier("P0047", "expected variant name")?;
            let binding = if self.take(&TokenKind::LeftParen) {
                let (name, _) = self.take_identifier("P0048", "expected pattern binding")?;
                self.expect(
                    &TokenKind::RightParen,
                    "P0049",
                    "expected `)` after pattern binding",
                )?;
                Some(name)
            } else {
                None
            };
            self.expect(&TokenKind::FatArrow, "P0050", "expected `=>` after pattern")?;
            let value = self.parse_expression(1)?;
            let end = self
                .expect(&TokenKind::Comma, "P0051", "expected `,` after match arm")?
                .span;
            arms.push(MatchArm {
                variant,
                binding,
                value,
                span: arm_start.join(end),
            });
        }
        let end = self
            .expect(
                &TokenKind::RightBrace,
                "P0052",
                "expected `}` after match arms",
            )?
            .span;
        Some(Expr {
            kind: ExprKind::Match { target, arms },
            span: start.join(end),
        })
    }

    fn binary_operator(&self) -> Option<(BinaryOp, u8)> {
        Some(match self.current().kind {
            TokenKind::OrOr => (BinaryOp::Or, 1),
            TokenKind::AndAnd => (BinaryOp::And, 2),
            TokenKind::EqualEqual => (BinaryOp::Equal, 3),
            TokenKind::BangEqual => (BinaryOp::NotEqual, 3),
            TokenKind::Less => (BinaryOp::Less, 4),
            TokenKind::LessEqual => (BinaryOp::LessEqual, 4),
            TokenKind::Greater => (BinaryOp::Greater, 4),
            TokenKind::GreaterEqual => (BinaryOp::GreaterEqual, 4),
            TokenKind::Plus => (BinaryOp::Add, 5),
            TokenKind::Minus => (BinaryOp::Subtract, 5),
            TokenKind::Star => (BinaryOp::Multiply, 6),
            TokenKind::Slash => (BinaryOp::Divide, 6),
            _ => return None,
        })
    }

    fn take_identifier(
        &mut self,
        code: &'static str,
        message: &'static str,
    ) -> Option<(String, Span)> {
        if let TokenKind::Identifier(name) = &self.current().kind {
            let name = name.clone();
            let span = self.advance().span;
            Some((name, span))
        } else {
            self.error(code, message);
            None
        }
    }
    fn expect(
        &mut self,
        expected: &TokenKind,
        code: &'static str,
        message: &'static str,
    ) -> Option<&Token> {
        if self.at(expected) {
            Some(self.advance())
        } else {
            self.error(code, message);
            None
        }
    }
    fn error(&mut self, code: &'static str, message: &'static str) {
        self.diagnostics
            .push(Diagnostic::error(code, message, self.current().span));
    }
    fn synchronize_top_level(&mut self) {
        while !self.at(&TokenKind::Eof)
            && !self.at(&TokenKind::Let)
            && !self.at(&TokenKind::Fn)
            && !self.at(&TokenKind::Record)
            && !self.at(&TokenKind::Union)
        {
            self.advance();
        }
    }
    fn synchronize_block(&mut self) {
        while !self.at(&TokenKind::Eof)
            && !self.at(&TokenKind::RightBrace)
            && !self.at(&TokenKind::Let)
        {
            self.advance();
        }
    }
    fn take(&mut self, kind: &TokenKind) -> bool {
        if self.at(kind) {
            self.advance();
            true
        } else {
            false
        }
    }
    fn at(&self, kind: &TokenKind) -> bool {
        std::mem::discriminant(&self.current().kind) == std::mem::discriminant(kind)
    }
    fn current(&self) -> &Token {
        &self.tokens[self.current]
    }
    fn advance(&mut self) -> &Token {
        let index = self.current;
        if !self.at(&TokenKind::Eof) {
            self.current += 1;
        }
        &self.tokens[index]
    }
}
