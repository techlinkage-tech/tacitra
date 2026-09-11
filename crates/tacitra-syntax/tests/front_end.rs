use tacitra_syntax::{format_program, format_source, parse, Diagnostic, ExprKind, Item};

const RICH_SOURCE: &str = r"
record User { name: String, active: Bool, }
union State { Ready, Failed(String), }
fn pick(user: User,state: State)->Result[Option[String],String]{
  if user.active { match state { Ready => Ok(Some(user.name)), Failed(message) => Err(message), } }
  else { Ok(None()) }
}
";

#[test]
fn parses_milestone_two_constructs() {
    let result = parse(RICH_SOURCE);
    assert!(result.diagnostics.is_empty(), "{:?}", result.diagnostics);
    assert_eq!(result.program.items.len(), 3);
    let Item::Function(function) = &result.program.items[2] else {
        panic!("expected function")
    };
    assert_eq!(
        function
            .parameters
            .iter()
            .map(|value| value.name.as_str())
            .collect::<Vec<_>>(),
        ["user", "state"]
    );
    assert!(matches!(function.body.result.kind, ExprKind::If { .. }));
}

#[test]
fn rejects_invalid_syntax_with_stable_codes() {
    let result = parse("let = 1;\nfn f(a Int) -> Int { a }\n@");
    let codes = result
        .diagnostics
        .iter()
        .map(|diagnostic| diagnostic.code)
        .collect::<Vec<_>>();
    assert_eq!(codes, ["P0002", "P0016", "L0001"]);
    assert!(result
        .diagnostics
        .windows(2)
        .all(|pair| pair[0].span.start.byte <= pair[1].span.start.byte));
}

#[test]
fn parse_format_parse_preserves_semantics() {
    let first = parse(RICH_SOURCE);
    assert!(first.diagnostics.is_empty(), "{:?}", first.diagnostics);
    let formatted = format_program(&first.program);
    let second = parse(&formatted);
    assert!(
        second.diagnostics.is_empty(),
        "{formatted}\n{:?}",
        second.diagnostics
    );
    assert!(first.program.semantic_eq(&second.program));
}

#[test]
fn formatter_is_idempotent() {
    let once = format_source("fn add(a:Int,b:Int)->Int{a+b}\nlet answer=add(40,2);").unwrap();
    let twice = format_source(&once).unwrap();
    assert_eq!(once, twice);
    assert_eq!(
        once,
        "fn add(a: Int, b: Int) -> Int {\n  a + b\n}\n\nlet answer = add(40, 2);\n"
    );
}

#[test]
fn diagnostics_are_deterministic_and_json_is_stable() {
    let first = parse("let x = @; let y = ;").diagnostics;
    let second = parse("let x = @; let y = ;").diagnostics;
    assert_eq!(first, second);
    let json = first.iter().map(Diagnostic::to_json).collect::<Vec<_>>();
    assert!(json[0].starts_with("{\"code\":\"L0001\",\"severity\":\"error\""));
    assert_eq!(
        first
            .iter()
            .map(|diagnostic| diagnostic.code)
            .collect::<Vec<_>>(),
        ["L0001", "P0015", "P0015"]
    );
}

#[test]
fn formatter_keeps_right_nested_binary_semantics() {
    let first = parse("let x = 1 - (2 - 3);");
    let formatted = format_program(&first.program);
    assert_eq!(formatted, "let x = 1 - (2 - 3);\n");
    assert!(first.program.semantic_eq(&parse(&formatted).program));
}

#[test]
fn ast_spans_include_grouping_and_line_positions() {
    let result = parse("fn f() -> Int {\n  (1 + 2)\n}\n");
    assert!(result.diagnostics.is_empty());
    let Item::Function(function) = &result.program.items[0] else {
        panic!("expected function")
    };
    assert_eq!(function.span.start.line, 1);
    assert_eq!(function.span.end.line, 3);
    assert_eq!(function.body.result.span.start.line, 2);
    assert_eq!(function.body.result.span.start.column, 3);
    assert_eq!(function.body.result.span.end.column, 10);
}

#[test]
fn line_comments_are_nonsemantic_and_format_away() {
    let source = "// module\nfn main() -> Int { // result\n  42 // value\n}\n";
    assert_eq!(
        format_source(source).unwrap(),
        "fn main() -> Int {\n  42\n}\n"
    );
}
