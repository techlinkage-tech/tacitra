mod ai;
mod candidate;
mod model;
mod patch;
mod query;

pub use ai::{
    apply_typed_edit, compact_legacy_patch, compact_typed_edit, expand_typed_edit,
    parse_typed_edit, repair_context, task_context_capsule, task_context_size, validate_typed_edit,
    RepairContext, TypedEditDocument,
};
pub use candidate::{function_body_edit, parse_named_typed_edit};
pub use model::{AgentError, SemanticModule};
pub use patch::{apply_patch, parse_patch, validate_patch, PatchDocument, PatchOutcome};
pub use query::{
    module_summary, symbol_describe, symbol_edit_context, symbol_references, type_describe,
};
