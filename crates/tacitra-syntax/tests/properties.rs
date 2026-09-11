use std::panic::{catch_unwind, AssertUnwindSafe};

use tacitra_syntax::{format_source, parse};

fn next(state: &mut u64) -> u64 {
    *state = state
        .wrapping_mul(6_364_136_223_846_793_005)
        .wrapping_add(1_442_695_040_888_963_407);
    *state
}

fn expression(state: &mut u64, depth: usize) -> String {
    if depth == 0 {
        return (next(state) % 100).to_string();
    }
    let left = expression(state, depth - 1);
    let right = expression(state, depth - 1);
    let index = usize::try_from(next(state) % 4).unwrap();
    let op = ["+", "-", "*", "/"][index];
    format!("({left}{op}({right}+1))")
}

#[test]
fn generated_programs_preserve_semantics_and_format_idempotently() {
    for seed in 0..256_u64 {
        let mut state = seed;
        let source = format!(
            "// seed {seed}\nfn compute(value:Int)->Int{{let offset={};value+offset}}\nfn main()->Int{{compute({})}}",
            expression(&mut state, 2),
            next(&mut state) % 100
        );
        let first = parse(&source);
        assert!(
            first.diagnostics.is_empty(),
            "seed {seed}: {:?}",
            first.diagnostics
        );
        let formatted = format_source(&source).expect("generated input should format");
        assert_eq!(format_source(&formatted).unwrap(), formatted, "seed {seed}");
        let second = parse(&formatted);
        assert!(first.program.semantic_eq(&second.program), "seed {seed}");
    }
}

#[test]
fn arbitrary_utf8_source_never_panics() {
    for seed in 0..1_024_u64 {
        let mut state = seed;
        let length = (next(&mut state) % 192) as usize;
        let mut source = String::new();
        for _ in 0..length {
            let scalar = match next(&mut state) % 6 {
                0 => (next(&mut state) % 128) as u32,
                1 => 0x80 + (next(&mut state) % (0x7ff - 0x80)) as u32,
                2 => 0x800 + (next(&mut state) % (0xd7ff - 0x800)) as u32,
                _ => 32 + (next(&mut state) % 95) as u32,
            };
            source.push(char::from_u32(scalar).unwrap_or('\u{fffd}'));
        }
        let outcome = catch_unwind(AssertUnwindSafe(|| {
            let parsed = parse(&source);
            if parsed.diagnostics.is_empty() {
                let formatted = format_source(&source).unwrap();
                assert!(parse(&formatted).diagnostics.is_empty());
            }
        }));
        assert!(outcome.is_ok(), "parser panicked for seed {seed}");
    }
}
