use crate::ast::{quote_json, span_json, Span};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Severity {
    Error,
}

impl Severity {
    const fn text(self) -> &'static str {
        match self {
            Self::Error => "error",
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Diagnostic {
    pub code: &'static str,
    pub severity: Severity,
    pub message: String,
    pub span: Span,
    pub expected_type: Option<String>,
    pub actual_type: Option<String>,
}

impl Diagnostic {
    #[must_use]
    pub fn error(code: &'static str, message: impl Into<String>, span: Span) -> Self {
        Self {
            code,
            severity: Severity::Error,
            message: message.into(),
            span,
            expected_type: None,
            actual_type: None,
        }
    }

    #[must_use]
    pub fn typed(
        code: &'static str,
        message: impl Into<String>,
        span: Span,
        expected_type: impl Into<String>,
        actual_type: impl Into<String>,
    ) -> Self {
        Self {
            code,
            severity: Severity::Error,
            message: message.into(),
            span,
            expected_type: Some(expected_type.into()),
            actual_type: Some(actual_type.into()),
        }
    }

    #[must_use]
    pub fn to_json(&self) -> String {
        format!(
            "{{\"code\":{},\"severity\":{},\"message\":{},\"span\":{},\"expected_type\":{},\"actual_type\":{}}}",
            quote_json(self.code),
            quote_json(self.severity.text()),
            quote_json(&self.message),
            span_json(self.span),
            self.expected_type.as_ref().map_or_else(|| "null".to_owned(), |value| quote_json(value)),
            self.actual_type.as_ref().map_or_else(|| "null".to_owned(), |value| quote_json(value))
        )
    }

    #[must_use]
    pub fn render_human(&self, path: &str, source: &str) -> String {
        let line = source
            .lines()
            .nth(self.span.start.line.saturating_sub(1))
            .unwrap_or("");
        let width = self
            .span
            .end
            .column
            .saturating_sub(self.span.start.column)
            .max(1);
        let marker = format!(
            "{}{}",
            " ".repeat(self.span.start.column.saturating_sub(1)),
            "^".repeat(width)
        );
        let types = match (&self.expected_type, &self.actual_type) {
            (Some(expected), Some(actual)) => format!(" (expected `{expected}`, found `{actual}`)"),
            _ => String::new(),
        };
        let message = format!("{}{types}", self.message);
        format!(
            "{path}:{}:{}: {}[{}]: {}\n  |\n{:>2} | {line}\n  | {marker}",
            self.span.start.line,
            self.span.start.column,
            self.severity.text(),
            self.code,
            message,
            self.span.start.line
        )
    }
}

pub(crate) fn sort_diagnostics(diagnostics: &mut [Diagnostic]) {
    diagnostics.sort_by(|left, right| {
        (left.span.start.byte, left.code, left.message.as_str()).cmp(&(
            right.span.start.byte,
            right.code,
            right.message.as_str(),
        ))
    });
}
