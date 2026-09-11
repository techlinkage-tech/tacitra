mod manifest;
mod query;
mod transport;
mod value;

pub use manifest::{
    parse_manifest, validate_manifest, CallMode, Export, ExternalType, Manifest, ManifestField,
    Ownership, Parameter, Transport, UsageExample,
};
pub use query::{call_context, export_describe, manifest_summary};
pub use transport::{invoke, CallOutcome, InvocationPolicy};
pub use value::{decode_bytes, encode_bytes, validate_value};

use serde_json::{json, Value};

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InteropError {
    pub code: &'static str,
    pub message: String,
    pub detail: Option<Value>,
}

impl InteropError {
    #[must_use]
    pub fn new(code: &'static str, message: impl Into<String>, detail: Option<Value>) -> Self {
        Self {
            code,
            message: message.into(),
            detail,
        }
    }

    #[must_use]
    pub fn to_json(&self) -> String {
        serde_json::to_string(&json!({
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        }))
        .unwrap_or_default()
    }
}
