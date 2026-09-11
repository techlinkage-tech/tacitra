mod check;
mod hir;
mod interpreter;

pub use check::{analyze, Analysis};
pub use hir::{
    CallTarget, HirBinding, HirBlock, HirExpr, HirExprKind, HirFunction, HirMatchArm, HirParameter,
    HirProgram, RecordDef, SymbolId, Type, UnionDef, VariantDef,
};
pub use interpreter::{execute_main, Value};
