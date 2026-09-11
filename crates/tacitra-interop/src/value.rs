use crate::{ExternalType, InteropError};
use serde_json::Value;

/// Validates a canonical JSON boundary value against a manifest type.
///
/// # Errors
///
/// Returns `I0003` with a value path when the representation or range is invalid.
pub fn validate_value(ty: &ExternalType, value: &Value, path: &str) -> Result<(), InteropError> {
    let valid = match ty {
        ExternalType::Bool => value.is_boolean(),
        ExternalType::Int { signed, bits } => valid_integer(value, *signed, *bits),
        ExternalType::Float { bits } => valid_float(value, *bits),
        ExternalType::String => value.is_string(),
        ExternalType::Bytes => value
            .as_object()
            .filter(|object| object.len() == 1)
            .and_then(|object| object.get("$bytes"))
            .and_then(Value::as_str)
            .is_some_and(|encoded| decode_bytes(encoded).is_ok()),
        ExternalType::List { element } => value.as_array().is_some_and(|values| {
            values.iter().enumerate().all(|(index, value)| {
                validate_value(element, value, &format!("{path}[{index}]")).is_ok()
            })
        }),
        ExternalType::Record { fields, .. } => value.as_object().is_some_and(|object| {
            object.len() == fields.len()
                && fields.iter().all(|field| {
                    object.get(&field.name).is_some_and(|value| {
                        validate_value(&field.ty, value, &format!("{path}.{}", field.name)).is_ok()
                    })
                })
        }),
        ExternalType::Option { value: inner } => {
            tagged(value, "$some")
                .is_some_and(|some| validate_value(inner, some, &format!("{path}.$some")).is_ok())
                || value
                    .as_object()
                    .filter(|object| object.len() == 1)
                    .and_then(|object| object.get("$none"))
                    == Some(&Value::Bool(true))
        }
        ExternalType::Result { ok, error } => {
            tagged(value, "$ok")
                .is_some_and(|result| validate_value(ok, result, &format!("{path}.$ok")).is_ok())
                || tagged(value, "$err").is_some_and(|result| {
                    validate_value(error, result, &format!("{path}.$err")).is_ok()
                })
        }
        ExternalType::Opaque { name } => value
            .as_object()
            .filter(|object| object.len() == 1)
            .and_then(|object| object.get("$handle"))
            .and_then(Value::as_object)
            .filter(|handle| handle.len() == 2)
            .is_some_and(|handle| {
                handle.get("type").and_then(Value::as_str) == Some(name)
                    && handle
                        .get("id")
                        .and_then(Value::as_str)
                        .is_some_and(|id| !id.is_empty())
            }),
    };
    if valid {
        Ok(())
    } else {
        Err(InteropError::new(
            "I0003",
            format!("value at `{path}` does not match the declared type"),
            Some(serde_json::json!({ "path": path, "type": ty })),
        ))
    }
}

fn tagged<'a>(value: &'a Value, tag: &str) -> Option<&'a Value> {
    value
        .as_object()
        .filter(|object| object.len() == 1)
        .and_then(|object| object.get(tag))
}

fn valid_integer(value: &Value, signed: bool, bits: u8) -> bool {
    if signed {
        let Some(number) = value.as_i64() else {
            return false;
        };
        if bits == 64 {
            true
        } else {
            let limit = 1_i64 << (bits - 1);
            (-limit..limit).contains(&number)
        }
    } else {
        let Some(number) = value.as_u64() else {
            return false;
        };
        bits == 64 || number < (1_u64 << bits)
    }
}

fn valid_float(value: &Value, bits: u8) -> bool {
    value.as_f64().is_some_and(|number| {
        number.is_finite() && (bits == 64 || number.abs() <= f64::from(f32::MAX))
    })
}

#[must_use]
pub fn encode_bytes(bytes: &[u8]) -> String {
    const ALPHABET: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut output = String::with_capacity(bytes.len().div_ceil(3) * 4);
    for chunk in bytes.chunks(3) {
        let first = chunk[0];
        let second = chunk.get(1).copied().unwrap_or(0);
        let third = chunk.get(2).copied().unwrap_or(0);
        output.push(char::from(ALPHABET[usize::from(first >> 2)]));
        output.push(char::from(
            ALPHABET[usize::from(((first & 0x03) << 4) | (second >> 4))],
        ));
        output.push(if chunk.len() > 1 {
            char::from(ALPHABET[usize::from(((second & 0x0f) << 2) | (third >> 6))])
        } else {
            '='
        });
        output.push(if chunk.len() > 2 {
            char::from(ALPHABET[usize::from(third & 0x3f)])
        } else {
            '='
        });
    }
    output
}

/// Decodes the canonical padded base64 representation used for `Bytes`.
///
/// # Errors
///
/// Returns `I0003` for malformed or non-canonical base64.
pub fn decode_bytes(encoded: &str) -> Result<Vec<u8>, InteropError> {
    if encoded.len() % 4 != 0 {
        return Err(bytes_error());
    }
    let bytes = encoded.as_bytes();
    let mut output = Vec::with_capacity(encoded.len() / 4 * 3);
    for (index, chunk) in bytes.chunks(4).enumerate() {
        let last = index + 1 == bytes.len() / 4;
        let a = base64_value(chunk[0]).ok_or_else(bytes_error)?;
        let b = base64_value(chunk[1]).ok_or_else(bytes_error)?;
        let c_padding = chunk[2] == b'=';
        let d_padding = chunk[3] == b'=';
        if c_padding && !d_padding || d_padding && !last {
            return Err(bytes_error());
        }
        let c = if c_padding {
            0
        } else {
            base64_value(chunk[2]).ok_or_else(bytes_error)?
        };
        let d = if d_padding {
            0
        } else {
            base64_value(chunk[3]).ok_or_else(bytes_error)?
        };
        output.push((a << 2) | (b >> 4));
        if !c_padding {
            output.push((b << 4) | (c >> 2));
        }
        if !d_padding {
            output.push((c << 6) | d);
        }
    }
    if encode_bytes(&output) != encoded {
        return Err(bytes_error());
    }
    Ok(output)
}

fn base64_value(byte: u8) -> Option<u8> {
    match byte {
        b'A'..=b'Z' => Some(byte - b'A'),
        b'a'..=b'z' => Some(byte - b'a' + 26),
        b'0'..=b'9' => Some(byte - b'0' + 52),
        b'+' => Some(62),
        b'/' => Some(63),
        _ => None,
    }
}

fn bytes_error() -> InteropError {
    InteropError::new("I0003", "invalid canonical base64 bytes", None)
}
