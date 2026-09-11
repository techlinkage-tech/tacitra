use tacitra_semantics::{analyze, execute_main, Type, Value};
use tacitra_syntax::parse;

fn analyze_source(source: &str) -> tacitra_semantics::Analysis {
    let parsed = parse(source);
    assert!(
        parsed.diagnostics.is_empty(),
        "parse errors: {:?}",
        parsed.diagnostics
    );
    analyze(&parsed.program)
}

#[test]
fn resolves_lexical_scopes_and_builds_typed_hir() {
    let analysis = analyze_source(
        r"
        fn choose(value: Int) -> Int {
          let outer = value + 1;
          if true { let value = outer * 2; value } else { outer }
        }
        fn main() -> Int { choose(20) }
    ",
    );
    assert!(
        analysis.diagnostics.is_empty(),
        "{:?}",
        analysis.diagnostics
    );
    let hir = analysis.program.unwrap();
    let main = hir.functions.get(&hir.main.unwrap()).unwrap();
    assert_eq!(main.return_type, Type::Int);
    assert_eq!(execute_main(&hir).unwrap(), Value::Int(42));
}

#[test]
fn reports_duplicate_and_undefined_names_in_source_order() {
    let source = "fn main() -> Int { let x = 1; let x = 2; missing + x }";
    let first = analyze_source(source).diagnostics;
    let second = analyze_source(source).diagnostics;
    assert_eq!(first, second);
    assert_eq!(
        first.iter().map(|value| value.code).collect::<Vec<_>>(),
        ["N0001", "N0002"]
    );
    assert!(first
        .windows(2)
        .all(|pair| pair[0].span.start.byte <= pair[1].span.start.byte));
}

#[test]
fn type_errors_include_expected_and_actual_types_in_json() {
    let analysis = analyze_source("fn bad(x: Int) -> Bool { x + true }");
    assert!(analysis.program.is_none());
    assert_eq!(
        analysis
            .diagnostics
            .iter()
            .map(|value| value.code)
            .collect::<Vec<_>>(),
        ["T0001", "T0001"]
    );
    for diagnostic in &analysis.diagnostics {
        assert!(diagnostic.expected_type.is_some());
        assert!(diagnostic.actual_type.is_some());
        let json = diagnostic.to_json();
        assert!(json.contains("\"expected_type\":"));
        assert!(json.contains("\"actual_type\":"));
    }
}

#[test]
fn checks_function_calls_and_operator_types() {
    let analysis = analyze_source("fn f(x: Int) -> Int { x * 2 } fn main() -> Int { f() }");
    assert!(analysis.program.is_none());
    assert_eq!(
        analysis
            .diagnostics
            .iter()
            .map(|value| value.code)
            .collect::<Vec<_>>(),
        ["T0003"]
    );
    assert_eq!(analysis.diagnostics[0].expected_type.as_deref(), Some("1"));
    assert_eq!(analysis.diagnostics[0].actual_type.as_deref(), Some("0"));
}

#[test]
fn rejects_non_exhaustive_and_invalid_union_patterns() {
    let analysis = analyze_source(
        r#"
        union State { Ready, Failed(String), }
        fn inspect(state: State) -> String {
          match state { Ready(value) => "ready", }
        }
    "#,
    );
    assert!(analysis.program.is_none());
    assert_eq!(
        analysis
            .diagnostics
            .iter()
            .map(|value| value.code)
            .collect::<Vec<_>>(),
        ["T0012", "T0014"]
    );
}

#[test]
fn executes_option_result_record_union_and_match() {
    let analysis = analyze_source(include_str!("../../../examples/algebraic.taci"));
    assert!(
        analysis.diagnostics.is_empty(),
        "{:?}",
        analysis.diagnostics
    );
    assert_eq!(
        execute_main(&analysis.program.unwrap()).unwrap(),
        Value::String("Ada".to_owned())
    );
}

#[test]
fn executes_none_err_and_unit_values() {
    let none = analyze_source(
        "fn absent() -> Option[Int] { None() } fn main() -> Int { match absent() { Some(value) => value, None => 7, } }",
    );
    assert_eq!(execute_main(&none.program.unwrap()).unwrap(), Value::Int(7));

    let error = analyze_source(
        "fn fail() -> Result[String, String] { Err(\"bad\") } fn main() -> String { match fail() { Ok(value) => value, Err(reason) => reason, } }",
    );
    assert_eq!(
        execute_main(&error.program.unwrap()).unwrap(),
        Value::String("bad".to_owned())
    );

    let unit = analyze_source("fn main() -> Unit { () }");
    assert_eq!(execute_main(&unit.program.unwrap()).unwrap(), Value::Unit);
}

#[test]
fn invalid_program_never_produces_executable_hir() {
    let analysis = analyze_source("fn main() -> Int { false }");
    assert!(analysis.program.is_none());
    assert_eq!(analysis.diagnostics[0].code, "T0001");
}

#[test]
fn if_branches_must_match_the_declared_result() {
    let analysis = analyze_source("fn main() -> Int { if true { 1 } else { false } }");
    assert!(analysis.program.is_none());
    assert_eq!(analysis.diagnostics.len(), 1);
    assert_eq!(
        analysis.diagnostics[0].expected_type.as_deref(),
        Some("Int")
    );
    assert_eq!(analysis.diagnostics[0].actual_type.as_deref(), Some("Bool"));
}

#[test]
fn runtime_failures_have_stable_codes() {
    let analysis = analyze_source("fn main() -> Int { 1 / 0 }");
    let error = execute_main(&analysis.program.unwrap()).unwrap_err();
    assert_eq!(error.code, "R0001");
}

#[test]
fn top_level_initialization_resolves_dependencies_deterministically() {
    let analysis = analyze_source(
        "let first = later(); let answer = 41; fn later() -> Int { answer + 1 } fn main() -> Int { first }",
    );
    assert!(
        analysis.diagnostics.is_empty(),
        "{:?}",
        analysis.diagnostics
    );
    assert_eq!(
        execute_main(&analysis.program.unwrap()).unwrap(),
        Value::Int(42)
    );
}

#[test]
fn cyclic_top_level_initialization_is_a_runtime_error() {
    let analysis =
        analyze_source("let value = load(); fn load() -> Int { value } fn main() -> Int { value }");
    assert!(
        analysis.diagnostics.is_empty(),
        "{:?}",
        analysis.diagnostics
    );
    assert_eq!(
        execute_main(&analysis.program.unwrap()).unwrap_err().code,
        "R0004"
    );
}

#[test]
fn rejects_noncanonical_algebraic_order() {
    let analysis = analyze_source(
        r"
        record Pair { first: Int, second: Int, }
        fn main() -> Int {
          let pair = new Pair { second: 2, first: 1 };
          match Some(pair.first) { None => 0, Some(value) => value, }
        }
        ",
    );
    assert_eq!(
        analysis
            .diagnostics
            .iter()
            .map(|value| value.code)
            .collect::<Vec<_>>(),
        ["T0017", "T0018"]
    );
}
