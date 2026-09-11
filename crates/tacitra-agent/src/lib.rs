mod model;
mod patch;
mod query;

pub use model::{AgentError, SemanticModule};
pub use patch::{apply_patch, parse_patch, validate_patch, PatchDocument, PatchOutcome};
pub use query::{
    module_summary, symbol_describe, symbol_edit_context, symbol_references, type_describe,
};
