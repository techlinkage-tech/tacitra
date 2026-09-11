use std::{collections::BTreeMap, fmt};
use tacitra_syntax::{BinaryOp, Span, UnaryOp};

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct SymbolId(pub u32);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Type {
    Int,
    Bool,
    String,
    Unit,
    Option(Box<Type>),
    Result(Box<Type>, Box<Type>),
    Record(String),
    Union(String),
    Function(Vec<Type>, Box<Type>),
    Error,
}

impl fmt::Display for Type {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Int => write!(formatter, "Int"),
            Self::Bool => write!(formatter, "Bool"),
            Self::String => write!(formatter, "String"),
            Self::Unit => write!(formatter, "Unit"),
            Self::Option(inner) => write!(formatter, "Option[{inner}]"),
            Self::Result(ok, error) => write!(formatter, "Result[{ok}, {error}]"),
            Self::Record(name) | Self::Union(name) => write!(formatter, "{name}"),
            Self::Function(parameters, result) => {
                write!(formatter, "fn(")?;
                for (index, parameter) in parameters.iter().enumerate() {
                    if index > 0 {
                        write!(formatter, ", ")?;
                    }
                    write!(formatter, "{parameter}")?;
                }
                write!(formatter, ") -> {result}")
            }
            Self::Error => write!(formatter, "<error>"),
        }
    }
}

#[derive(Clone, Debug)]
pub struct HirProgram {
    pub records: BTreeMap<String, RecordDef>,
    pub unions: BTreeMap<String, UnionDef>,
    pub functions: BTreeMap<SymbolId, HirFunction>,
    pub globals: Vec<HirBinding>,
    pub main: Option<SymbolId>,
}

#[derive(Clone, Debug)]
pub struct RecordDef {
    pub fields: Vec<(String, Type)>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct UnionDef {
    pub variants: Vec<VariantDef>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct VariantDef {
    pub name: String,
    pub payload: Option<Type>,
}

#[derive(Clone, Debug)]
pub struct HirFunction {
    pub id: SymbolId,
    pub name: String,
    pub parameters: Vec<HirParameter>,
    pub return_type: Type,
    pub body: HirBlock,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct HirParameter {
    pub id: SymbolId,
    pub name: String,
    pub ty: Type,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct HirBinding {
    pub id: SymbolId,
    pub name: String,
    pub value: HirExpr,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct HirBlock {
    pub bindings: Vec<HirBinding>,
    pub result: Box<HirExpr>,
}

#[derive(Clone, Debug)]
pub struct HirExpr {
    pub kind: HirExprKind,
    pub ty: Type,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub enum HirExprKind {
    Integer(i64),
    Boolean(bool),
    String(String),
    Unit,
    Name(SymbolId),
    Unary {
        op: UnaryOp,
        operand: Box<HirExpr>,
    },
    Binary {
        left: Box<HirExpr>,
        op: BinaryOp,
        right: Box<HirExpr>,
    },
    Call {
        target: CallTarget,
        arguments: Vec<HirExpr>,
    },
    Field {
        target: Box<HirExpr>,
        name: String,
    },
    If {
        condition: Box<HirExpr>,
        then_block: HirBlock,
        else_block: HirBlock,
    },
    Record {
        name: String,
        fields: Vec<(String, HirExpr)>,
    },
    Match {
        target: Box<HirExpr>,
        arms: Vec<HirMatchArm>,
    },
    Error,
}

#[derive(Clone, Debug)]
pub enum CallTarget {
    Function(SymbolId),
    Some,
    None,
    Ok,
    Err,
    Variant {
        union_name: String,
        variant: String,
        has_payload: bool,
    },
}

#[derive(Clone, Debug)]
pub struct HirMatchArm {
    pub variant: String,
    pub binding: Option<SymbolId>,
    pub binding_name: Option<String>,
    pub value: HirExpr,
    pub span: Span,
}
