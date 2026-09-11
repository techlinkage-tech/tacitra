#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Position {
    pub byte: usize,
    pub line: usize,
    pub column: usize,
}

impl Default for Position {
    fn default() -> Self {
        Self {
            byte: 0,
            line: 1,
            column: 1,
        }
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct Span {
    pub start: Position,
    pub end: Position,
}

impl Span {
    #[must_use]
    pub const fn new(start: Position, end: Position) -> Self {
        Self { start, end }
    }
    #[must_use]
    pub const fn join(self, other: Self) -> Self {
        Self::new(self.start, other.end)
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct Program {
    pub items: Vec<Item>,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Item {
    Let(LetBinding),
    Function(Function),
    Record(RecordDecl),
    Union(UnionDecl),
}

impl Item {
    #[must_use]
    pub const fn span(&self) -> Span {
        match self {
            Self::Let(v) => v.span,
            Self::Function(v) => v.span,
            Self::Record(v) => v.span,
            Self::Union(v) => v.span,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TypeRef {
    pub kind: TypeRefKind,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum TypeRefKind {
    Named(String),
    Option(Box<TypeRef>),
    Result(Box<TypeRef>, Box<TypeRef>),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LetBinding {
    pub name: String,
    pub value: Expr,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Parameter {
    pub name: String,
    pub ty: TypeRef,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Function {
    pub name: String,
    pub parameters: Vec<Parameter>,
    pub return_type: TypeRef,
    pub body: Block,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RecordDecl {
    pub name: String,
    pub fields: Vec<FieldDecl>,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FieldDecl {
    pub name: String,
    pub ty: TypeRef,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UnionDecl {
    pub name: String,
    pub variants: Vec<VariantDecl>,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VariantDecl {
    pub name: String,
    pub payload: Option<TypeRef>,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Block {
    pub bindings: Vec<LetBinding>,
    pub result: Box<Expr>,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Expr {
    pub kind: ExprKind,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ExprKind {
    Integer(i64),
    Boolean(bool),
    String(String),
    Unit,
    Name(String),
    Unary {
        op: UnaryOp,
        operand: Box<Expr>,
    },
    Binary {
        left: Box<Expr>,
        op: BinaryOp,
        right: Box<Expr>,
    },
    Call {
        callee: Box<Expr>,
        arguments: Vec<Expr>,
    },
    Field {
        target: Box<Expr>,
        name: String,
    },
    If {
        condition: Box<Expr>,
        then_block: Block,
        else_block: Block,
    },
    Record {
        name: String,
        fields: Vec<FieldValue>,
    },
    Match {
        target: Box<Expr>,
        arms: Vec<MatchArm>,
    },
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FieldValue {
    pub name: String,
    pub value: Expr,
    pub span: Span,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MatchArm {
    pub variant: String,
    pub binding: Option<String>,
    pub value: Expr,
    pub span: Span,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum UnaryOp {
    Not,
    Negate,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BinaryOp {
    Or,
    And,
    Equal,
    NotEqual,
    Less,
    LessEqual,
    Greater,
    GreaterEqual,
    Add,
    Subtract,
    Multiply,
    Divide,
}

impl UnaryOp {
    #[must_use]
    pub const fn text(self) -> &'static str {
        match self {
            Self::Not => "!",
            Self::Negate => "-",
        }
    }
}

impl BinaryOp {
    #[must_use]
    pub const fn text(self) -> &'static str {
        match self {
            Self::Or => "||",
            Self::And => "&&",
            Self::Equal => "==",
            Self::NotEqual => "!=",
            Self::Less => "<",
            Self::LessEqual => "<=",
            Self::Greater => ">",
            Self::GreaterEqual => ">=",
            Self::Add => "+",
            Self::Subtract => "-",
            Self::Multiply => "*",
            Self::Divide => "/",
        }
    }
}

impl Program {
    #[must_use]
    pub fn semantic_eq(&self, other: &Self) -> bool {
        crate::formatter::format_program(self) == crate::formatter::format_program(other)
    }

    #[must_use]
    pub fn to_json(&self) -> String {
        let items = self
            .items
            .iter()
            .map(item_json)
            .collect::<Vec<_>>()
            .join(",");
        format!(
            "{{\"kind\":\"program\",\"span\":{},\"items\":[{items}]}}",
            span_json(self.span)
        )
    }
}

fn item_json(item: &Item) -> String {
    match item {
        Item::Let(value) => binding_json(value),
        Item::Function(value) => {
            let parameters = value
                .parameters
                .iter()
                .map(|parameter| {
                    format!(
                        "{{\"name\":{},\"type\":{},\"span\":{}}}",
                        quote_json(&parameter.name),
                        quote_json(&type_text(&parameter.ty)),
                        span_json(parameter.span)
                    )
                })
                .collect::<Vec<_>>()
                .join(",");
            format!(
                "{{\"kind\":\"function\",\"span\":{},\"name\":{},\"parameters\":[{parameters}],\"return_type\":{},\"body\":{}}}",
                span_json(value.span), quote_json(&value.name), quote_json(&type_text(&value.return_type)), block_json(&value.body)
            )
        }
        Item::Record(value) => {
            let fields = value
                .fields
                .iter()
                .map(|field| {
                    format!(
                        "{{\"name\":{},\"type\":{},\"span\":{}}}",
                        quote_json(&field.name),
                        quote_json(&type_text(&field.ty)),
                        span_json(field.span)
                    )
                })
                .collect::<Vec<_>>()
                .join(",");
            format!(
                "{{\"kind\":\"record\",\"span\":{},\"name\":{},\"fields\":[{fields}]}}",
                span_json(value.span),
                quote_json(&value.name)
            )
        }
        Item::Union(value) => {
            let variants = value
                .variants
                .iter()
                .map(|variant| {
                    format!(
                        "{{\"name\":{},\"payload_type\":{},\"span\":{}}}",
                        quote_json(&variant.name),
                        variant
                            .payload
                            .as_ref()
                            .map_or_else(|| "null".to_owned(), |ty| quote_json(&type_text(ty))),
                        span_json(variant.span)
                    )
                })
                .collect::<Vec<_>>()
                .join(",");
            format!(
                "{{\"kind\":\"union\",\"span\":{},\"name\":{},\"variants\":[{variants}]}}",
                span_json(value.span),
                quote_json(&value.name)
            )
        }
    }
}

fn binding_json(value: &LetBinding) -> String {
    format!(
        "{{\"kind\":\"let\",\"span\":{},\"name\":{},\"value\":{}}}",
        span_json(value.span),
        quote_json(&value.name),
        expr_json(&value.value)
    )
}

fn block_json(value: &Block) -> String {
    let bindings = value
        .bindings
        .iter()
        .map(binding_json)
        .collect::<Vec<_>>()
        .join(",");
    format!(
        "{{\"kind\":\"block\",\"span\":{},\"bindings\":[{bindings}],\"result\":{}}}",
        span_json(value.span),
        expr_json(&value.result)
    )
}

#[allow(clippy::too_many_lines)]
fn expr_json(value: &Expr) -> String {
    let span = span_json(value.span);
    match &value.kind {
        ExprKind::Integer(number) => {
            format!("{{\"kind\":\"integer\",\"span\":{span},\"value\":{number}}}")
        }
        ExprKind::Boolean(boolean) => {
            format!("{{\"kind\":\"boolean\",\"span\":{span},\"value\":{boolean}}}")
        }
        ExprKind::String(string) => format!(
            "{{\"kind\":\"string\",\"span\":{span},\"value\":{}}}",
            quote_json(string)
        ),
        ExprKind::Unit => format!("{{\"kind\":\"unit\",\"span\":{span}}}"),
        ExprKind::Name(name) => format!(
            "{{\"kind\":\"name\",\"span\":{span},\"value\":{}}}",
            quote_json(name)
        ),
        ExprKind::Unary { op, operand } => format!(
            "{{\"kind\":\"unary\",\"span\":{span},\"operator\":{},\"operand\":{}}}",
            quote_json(op.text()),
            expr_json(operand)
        ),
        ExprKind::Binary { left, op, right } => format!(
            "{{\"kind\":\"binary\",\"span\":{span},\"operator\":{},\"left\":{},\"right\":{}}}",
            quote_json(op.text()),
            expr_json(left),
            expr_json(right)
        ),
        ExprKind::Call { callee, arguments } => {
            let arguments = arguments
                .iter()
                .map(expr_json)
                .collect::<Vec<_>>()
                .join(",");
            format!(
                "{{\"kind\":\"call\",\"span\":{span},\"callee\":{},\"arguments\":[{arguments}]}}",
                expr_json(callee)
            )
        }
        ExprKind::Field { target, name } => format!(
            "{{\"kind\":\"field\",\"span\":{span},\"target\":{},\"name\":{}}}",
            expr_json(target),
            quote_json(name)
        ),
        ExprKind::If {
            condition,
            then_block,
            else_block,
        } => format!(
            "{{\"kind\":\"if\",\"span\":{span},\"condition\":{},\"then\":{},\"else\":{}}}",
            expr_json(condition),
            block_json(then_block),
            block_json(else_block)
        ),
        ExprKind::Record { name, fields } => {
            let fields = fields
                .iter()
                .map(|field| {
                    format!(
                        "{{\"name\":{},\"value\":{},\"span\":{}}}",
                        quote_json(&field.name),
                        expr_json(&field.value),
                        span_json(field.span)
                    )
                })
                .collect::<Vec<_>>()
                .join(",");
            format!(
                "{{\"kind\":\"record_value\",\"span\":{span},\"name\":{},\"fields\":[{fields}]}}",
                quote_json(name)
            )
        }
        ExprKind::Match { target, arms } => {
            let arms = arms
                .iter()
                .map(|arm| {
                    format!(
                        "{{\"variant\":{},\"binding\":{},\"value\":{},\"span\":{}}}",
                        quote_json(&arm.variant),
                        arm.binding
                            .as_ref()
                            .map_or_else(|| "null".to_owned(), |binding| quote_json(binding)),
                        expr_json(&arm.value),
                        span_json(arm.span)
                    )
                })
                .collect::<Vec<_>>()
                .join(",");
            format!(
                "{{\"kind\":\"match\",\"span\":{span},\"target\":{},\"arms\":[{arms}]}}",
                expr_json(target)
            )
        }
    }
}

fn type_text(value: &TypeRef) -> String {
    match &value.kind {
        TypeRefKind::Named(name) => name.clone(),
        TypeRefKind::Option(inner) => format!("Option[{}]", type_text(inner)),
        TypeRefKind::Result(ok, error) => {
            format!("Result[{}, {}]", type_text(ok), type_text(error))
        }
    }
}

pub(crate) fn quote_json(value: &str) -> String {
    let mut output = String::from("\"");
    for character in value.chars() {
        match character {
            '\"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            c if c.is_control() => output.push_str(&format!("\\u{:04x}", u32::from(c))),
            c => output.push(c),
        }
    }
    output.push('\"');
    output
}

pub(crate) fn span_json(span: Span) -> String {
    format!("{{\"start\":{{\"byte\":{},\"line\":{},\"column\":{}}},\"end\":{{\"byte\":{},\"line\":{},\"column\":{}}}}}",
        span.start.byte, span.start.line, span.start.column, span.end.byte, span.end.line, span.end.column)
}
