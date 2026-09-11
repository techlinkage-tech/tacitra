use crate::{Diagnostic, Position, Span};

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Token {
    pub kind: TokenKind,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum TokenKind {
    Let,
    Fn,
    Record,
    Union,
    If,
    Else,
    Match,
    New,
    True,
    False,
    Identifier(String),
    Integer(String),
    String(String),
    LeftParen,
    RightParen,
    LeftBrace,
    RightBrace,
    LeftBracket,
    RightBracket,
    Comma,
    Colon,
    Semicolon,
    Dot,
    Arrow,
    FatArrow,
    Equal,
    EqualEqual,
    Bang,
    BangEqual,
    Less,
    LessEqual,
    Greater,
    GreaterEqual,
    Plus,
    Minus,
    Star,
    Slash,
    AndAnd,
    OrOr,
    Eof,
}

#[must_use]
pub fn lex(source: &str) -> (Vec<Token>, Vec<Diagnostic>) {
    Scanner::new(source).scan()
}

struct Scanner<'a> {
    source: &'a str,
    byte: usize,
    line: usize,
    column: usize,
    tokens: Vec<Token>,
    diagnostics: Vec<Diagnostic>,
}

impl<'a> Scanner<'a> {
    fn new(source: &'a str) -> Self {
        Self {
            source,
            byte: 0,
            line: 1,
            column: 1,
            tokens: Vec::new(),
            diagnostics: Vec::new(),
        }
    }

    fn scan(mut self) -> (Vec<Token>, Vec<Diagnostic>) {
        while let Some(character) = self.peek() {
            if character.is_whitespace() {
                self.advance();
                continue;
            }
            if self.source[self.byte..].starts_with("//") {
                while self.peek().is_some_and(|value| value != '\n') {
                    self.advance();
                }
                continue;
            }
            let start = self.position();
            if character.is_ascii_alphabetic() || character == '_' {
                self.identifier(start);
                continue;
            }
            if character.is_ascii_digit() {
                self.integer(start);
                continue;
            }
            if character == '"' {
                self.string(start);
                continue;
            }
            self.advance();
            let kind = match character {
                '(' => Some(TokenKind::LeftParen),
                ')' => Some(TokenKind::RightParen),
                '{' => Some(TokenKind::LeftBrace),
                '}' => Some(TokenKind::RightBrace),
                '[' => Some(TokenKind::LeftBracket),
                ']' => Some(TokenKind::RightBracket),
                ',' => Some(TokenKind::Comma),
                ':' => Some(TokenKind::Colon),
                ';' => Some(TokenKind::Semicolon),
                '.' => Some(TokenKind::Dot),
                '+' => Some(TokenKind::Plus),
                '*' => Some(TokenKind::Star),
                '/' => Some(TokenKind::Slash),
                '-' if self.take('>') => Some(TokenKind::Arrow),
                '-' => Some(TokenKind::Minus),
                '=' if self.take('=') => Some(TokenKind::EqualEqual),
                '=' if self.take('>') => Some(TokenKind::FatArrow),
                '=' => Some(TokenKind::Equal),
                '!' if self.take('=') => Some(TokenKind::BangEqual),
                '!' => Some(TokenKind::Bang),
                '<' if self.take('=') => Some(TokenKind::LessEqual),
                '<' => Some(TokenKind::Less),
                '>' if self.take('=') => Some(TokenKind::GreaterEqual),
                '>' => Some(TokenKind::Greater),
                '&' if self.take('&') => Some(TokenKind::AndAnd),
                '|' if self.take('|') => Some(TokenKind::OrOr),
                _ => None,
            };
            if let Some(kind) = kind {
                self.tokens.push(Token {
                    kind,
                    span: Span::new(start, self.position()),
                });
            } else {
                self.diagnostics.push(Diagnostic::error(
                    "L0001",
                    format!("unexpected character `{character}`"),
                    Span::new(start, self.position()),
                ));
            }
        }
        let position = self.position();
        self.tokens.push(Token {
            kind: TokenKind::Eof,
            span: Span::new(position, position),
        });
        (self.tokens, self.diagnostics)
    }

    fn identifier(&mut self, start: Position) {
        while self
            .peek()
            .is_some_and(|c| c.is_ascii_alphanumeric() || c == '_')
        {
            self.advance();
        }
        let text = &self.source[start.byte..self.byte];
        let kind = match text {
            "let" => TokenKind::Let,
            "fn" => TokenKind::Fn,
            "record" => TokenKind::Record,
            "union" => TokenKind::Union,
            "if" => TokenKind::If,
            "else" => TokenKind::Else,
            "match" => TokenKind::Match,
            "new" => TokenKind::New,
            "true" => TokenKind::True,
            "false" => TokenKind::False,
            _ => TokenKind::Identifier(text.to_owned()),
        };
        self.tokens.push(Token {
            kind,
            span: Span::new(start, self.position()),
        });
    }

    fn integer(&mut self, start: Position) {
        while self.peek().is_some_and(|c| c.is_ascii_digit()) {
            self.advance();
        }
        self.tokens.push(Token {
            kind: TokenKind::Integer(self.source[start.byte..self.byte].to_owned()),
            span: Span::new(start, self.position()),
        });
    }

    fn string(&mut self, start: Position) {
        self.advance();
        let mut value = String::new();
        let mut terminated = false;
        while let Some(character) = self.peek() {
            if character == '"' {
                self.advance();
                terminated = true;
                break;
            }
            if character == '\n' {
                break;
            }
            self.advance();
            if character == '\\' {
                let Some(escaped) = self.advance() else { break };
                match escaped {
                    'n' => value.push('\n'),
                    'r' => value.push('\r'),
                    't' => value.push('\t'),
                    '"' => value.push('"'),
                    '\\' => value.push('\\'),
                    other => self.diagnostics.push(Diagnostic::error(
                        "L0003",
                        format!("unsupported escape `\\{other}`"),
                        Span::new(start, self.position()),
                    )),
                }
            } else {
                value.push(character);
            }
        }
        let span = Span::new(start, self.position());
        if terminated {
            self.tokens.push(Token {
                kind: TokenKind::String(value),
                span,
            });
        } else {
            self.diagnostics
                .push(Diagnostic::error("L0002", "unterminated string", span));
        }
    }

    fn peek(&self) -> Option<char> {
        self.source[self.byte..].chars().next()
    }
    fn take(&mut self, expected: char) -> bool {
        if self.peek() == Some(expected) {
            self.advance();
            true
        } else {
            false
        }
    }
    fn advance(&mut self) -> Option<char> {
        let character = self.peek()?;
        self.byte += character.len_utf8();
        if character == '\n' {
            self.line += 1;
            self.column = 1;
        } else {
            self.column += 1;
        }
        Some(character)
    }
    const fn position(&self) -> Position {
        Position {
            byte: self.byte,
            line: self.line,
            column: self.column,
        }
    }
}
