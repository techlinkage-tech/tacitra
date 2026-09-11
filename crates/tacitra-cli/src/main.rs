use std::{env, fs, path::Path, process::ExitCode};
use tacitra_agent::{
    apply_patch as apply_structural_patch, module_summary, parse_patch, symbol_describe,
    symbol_edit_context, symbol_references, type_describe, validate_patch, AgentError,
    SemanticModule,
};
use tacitra_interop::{
    call_context, export_describe, invoke, manifest_summary, parse_manifest, InteropError,
    InvocationPolicy,
};
use tacitra_semantics::{analyze, execute_main};
use tacitra_syntax::{format_program, parse, Diagnostic};

fn main() -> ExitCode {
    let arguments = env::args().skip(1).collect::<Vec<_>>();
    match run(&arguments) {
        Ok(()) => ExitCode::SUCCESS,
        Err(code) => ExitCode::from(code),
    }
}

fn run(arguments: &[String]) -> Result<(), u8> {
    let Some(command) = arguments.first().map(String::as_str) else {
        return usage();
    };
    match command {
        "parse" | "check" => parse_or_check(command, &arguments[1..]),
        "run" => run_program(&arguments[1..]),
        "module.summary"
        | "symbol.describe"
        | "symbol.edit-context"
        | "symbol.references"
        | "type.describe" => semantic_query(command, &arguments[1..]),
        "patch.validate" | "patch.apply" => patch_command(command, &arguments[1..]),
        "interop.inspect" | "external.summary" | "external.describe" | "external.call-context" => {
            interop_query(command, &arguments[1..])
        }
        "interop.call" => interop_call(&arguments[1..]),
        "fmt" => format(&arguments[1..]),
        "help" | "--help" | "-h" => {
            print_help();
            Ok(())
        }
        "--version" | "-V" => {
            println!("tacitra {} (experimental)", env!("CARGO_PKG_VERSION"));
            Ok(())
        }
        _ => {
            eprintln!("unknown command `{command}`");
            usage()
        }
    }
}

fn interop_query(command: &str, arguments: &[String]) -> Result<(), u8> {
    let needs_export = command == "external.describe" || command == "external.call-context";
    if (needs_export && arguments.len() != 2) || (!needs_export && arguments.len() != 1) {
        return usage();
    }
    let path = &arguments[0];
    let source = read(path)?;
    let manifest = parse_manifest(&source).map_err(|error| {
        emit_interop_error(&error);
        1
    })?;
    let output = match command {
        "external.describe" => export_describe(&manifest, &arguments[1]),
        "external.call-context" => call_context(&manifest, &arguments[1]),
        _ => Ok(manifest_summary(&manifest)),
    };
    match output {
        Ok(output) => {
            println!("{output}");
            Ok(())
        }
        Err(error) => {
            emit_interop_error(&error);
            Err(1)
        }
    }
}

fn interop_call(arguments: &[String]) -> Result<(), u8> {
    if arguments.len() < 3 {
        return usage();
    }
    let manifest_path = &arguments[0];
    let export = &arguments[1];
    let argument_path = &arguments[2];
    let manifest_source = read(manifest_path)?;
    let manifest = parse_manifest(&manifest_source).map_err(|error| {
        emit_interop_error(&error);
        1
    })?;
    let argument_source = read(argument_path)?;
    let values = serde_json::from_str(&argument_source).map_err(|error| {
        emit_interop_error(&InteropError::new(
            "I0003",
            format!("invalid argument JSON: {error}"),
            None,
        ));
        1
    })?;
    let mut policy = InvocationPolicy::from_manifest(&manifest);
    let mut index = 3;
    while index < arguments.len() {
        let Some(value) = arguments.get(index + 1) else {
            return usage();
        };
        match arguments[index].as_str() {
            "--timeout-ms" => {
                let timeout = value
                    .parse::<u64>()
                    .ok()
                    .filter(|value| (1..=300_000).contains(value));
                let Some(timeout) = timeout else {
                    return usage();
                };
                policy.timeout = std::time::Duration::from_millis(timeout);
            }
            "--allow-effect" => {
                policy.allowed_effects.insert(value.clone());
            }
            "--allow-capability" => {
                policy.allowed_capabilities.insert(value.clone());
            }
            _ => return usage(),
        }
        index += 2;
    }
    let directory = Path::new(manifest_path)
        .parent()
        .unwrap_or_else(|| Path::new("."));
    match invoke(&manifest, directory, export, &values, &policy) {
        Ok(outcome) => {
            println!("{}", outcome.to_json());
            Ok(())
        }
        Err(error) => {
            emit_interop_error(&error);
            Err(1)
        }
    }
}

fn emit_interop_error(error: &InteropError) {
    println!(
        "{{\"schema_version\":1,\"valid\":false,\"error\":{}}}",
        error.to_json()
    );
}

fn semantic_query(command: &str, arguments: &[String]) -> Result<(), u8> {
    let path = arguments.first().ok_or_else(usage_code)?;
    let selector = arguments.get(1).map(String::as_str);
    if (command == "module.summary" && arguments.len() != 1)
        || (command != "module.summary" && arguments.len() != 2)
    {
        return usage();
    }
    let source = read(path)?;
    let module = build_module(path, &source)?;
    let output = match command {
        "module.summary" => Ok(module_summary(&module)),
        "symbol.describe" => symbol_describe(&module, selector.expect("selector checked")),
        "symbol.edit-context" => symbol_edit_context(&module, selector.expect("selector checked")),
        "symbol.references" => symbol_references(&module, selector.expect("selector checked")),
        "type.describe" => type_describe(&module, selector.expect("selector checked")),
        _ => unreachable!(),
    };
    match output {
        Ok(value) => {
            println!("{value}");
            Ok(())
        }
        Err(error) => {
            emit_agent_error(&error);
            Err(1)
        }
    }
}

fn patch_command(command: &str, arguments: &[String]) -> Result<(), u8> {
    if arguments.len() != 2 {
        return usage();
    }
    let path = &arguments[0];
    let patch_path = &arguments[1];
    let source = read(path)?;
    let patch_source = read(patch_path)?;
    let module = build_module(path, &source)?;
    let document = match parse_patch(&patch_source) {
        Ok(value) => value,
        Err(error) => {
            emit_agent_error(&error);
            return Err(1);
        }
    };
    let result = if command == "patch.validate" {
        validate_patch(&module, &document)
    } else {
        apply_structural_patch(&module, &document)
    };
    match result {
        Ok(outcome) => {
            if command == "patch.apply" {
                write_atomic(path, &outcome.updated_source)?;
            }
            println!("{}", outcome.to_json());
            Ok(())
        }
        Err(error) => {
            emit_agent_error(&error);
            Err(1)
        }
    }
}

fn build_module(path: &str, source: &str) -> Result<SemanticModule, u8> {
    SemanticModule::build(source).map_err(|diagnostics| {
        emit_diagnostics(path, source, &diagnostics, true);
        1
    })
}

fn emit_agent_error(error: &AgentError) {
    println!(
        "{{\"schema_version\":1,\"valid\":false,\"error\":{}}}",
        error.to_json()
    );
}

fn usage_code() -> u8 {
    print_usage();
    2
}

fn parse_or_check(command: &str, arguments: &[String]) -> Result<(), u8> {
    let (json, path) = parse_flag_and_path(arguments, "--json")?;
    let source = read(path)?;
    let result = parse(&source);
    if !result.diagnostics.is_empty() {
        emit_diagnostics(path, &source, &result.diagnostics, json);
        return Err(1);
    }
    if command == "parse" {
        if json {
            println!("{}", result.program.to_json());
        } else {
            println!("{:#?}", result.program);
        }
    } else {
        let analysis = analyze(&result.program);
        if !analysis.diagnostics.is_empty() {
            emit_diagnostics(path, &source, &analysis.diagnostics, json);
            return Err(1);
        }
        if json {
            println!("{{\"schema_version\":1,\"valid\":true,\"diagnostics\":[]}}");
        }
    }
    Ok(())
}

fn run_program(arguments: &[String]) -> Result<(), u8> {
    let (json, path) = parse_flag_and_path(arguments, "--json")?;
    let source = read(path)?;
    let parsed = parse(&source);
    if !parsed.diagnostics.is_empty() {
        emit_diagnostics(path, &source, &parsed.diagnostics, json);
        return Err(1);
    }
    let analysis = analyze(&parsed.program);
    if !analysis.diagnostics.is_empty() {
        emit_diagnostics(path, &source, &analysis.diagnostics, json);
        return Err(1);
    }
    let program = analysis
        .program
        .expect("successful analysis must produce HIR");
    match execute_main(&program) {
        Ok(value) => {
            if json {
                println!("{}", value.to_json());
            } else {
                println!("{}", value.render());
            }
            Ok(())
        }
        Err(diagnostic) => {
            emit_diagnostics(path, &source, &[diagnostic], json);
            Err(1)
        }
    }
}

fn format(arguments: &[String]) -> Result<(), u8> {
    if arguments.len() == 1 {
        let path = &arguments[0];
        let source = read(path)?;
        let result = parse(&source);
        if !result.diagnostics.is_empty() {
            emit_diagnostics(path, &source, &result.diagnostics, false);
            return Err(1);
        }
        print!("{}", format_program(&result.program));
        return Ok(());
    }
    if arguments.len() == 2 && (arguments[0] == "--write" || arguments[0] == "--check") {
        let path = &arguments[1];
        let source = read(path)?;
        let result = parse(&source);
        if !result.diagnostics.is_empty() {
            emit_diagnostics(path, &source, &result.diagnostics, false);
            return Err(1);
        }
        let formatted = format_program(&result.program);
        if arguments[0] == "--write" {
            fs::write(path, formatted).map_err(|error| io_error(path, &error))?;
        } else if source != formatted {
            eprintln!("{path} is not canonically formatted");
            return Err(1);
        }
        return Ok(());
    }
    usage()
}

fn parse_flag_and_path<'a>(arguments: &'a [String], flag: &str) -> Result<(bool, &'a str), u8> {
    match arguments {
        [path] => Ok((false, path)),
        [given, path] if given == flag => Ok((true, path)),
        _ => usage(),
    }
}

fn read(path: &str) -> Result<String, u8> {
    fs::read_to_string(path).map_err(|error| io_error(path, &error))
}

fn write_atomic(path: &str, source: &str) -> Result<(), u8> {
    let target = Path::new(path);
    let name = target
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("module");
    let temporary = target.with_file_name(format!(".{name}.tacitra-{}.tmp", std::process::id()));
    fs::write(&temporary, source).map_err(|error| io_error(path, &error))?;
    let permissions = fs::metadata(target)
        .map_err(|error| io_error(path, &error))?
        .permissions();
    fs::set_permissions(&temporary, permissions).map_err(|error| io_error(path, &error))?;
    fs::rename(&temporary, target).map_err(|error| io_error(path, &error))
}

fn io_error(path: &str, error: &std::io::Error) -> u8 {
    eprintln!("{path}: error[IO0001]: {error}");
    2
}

fn emit_diagnostics(path: &str, source: &str, diagnostics: &[Diagnostic], json: bool) {
    if json {
        let body = diagnostics
            .iter()
            .map(Diagnostic::to_json)
            .collect::<Vec<_>>()
            .join(",");
        println!("{{\"schema_version\":1,\"valid\":false,\"diagnostics\":[{body}]}}");
    } else {
        for diagnostic in diagnostics {
            eprintln!("{}", diagnostic.render_human(path, source));
        }
    }
}

fn usage<T>() -> Result<T, u8> {
    print_usage();
    Err(2)
}

fn print_usage() {
    eprintln!("run `tacitra --help` for usage");
}

fn print_help() {
    println!("Tacitra {} (experimental)\n\nUsage:\n  tacitra COMMAND [OPTIONS]\n\nCompiler commands:\n  parse [--json] FILE       Parse and print the source-positioned AST\n  fmt [--write|--check] FILE\n                            Print, write, or verify canonical formatting\n  check [--json] FILE       Parse, resolve names, and type-check\n  run [--json] FILE         Execute a checked zero-argument main function\n\nSemantic commands:\n  module.summary FILE\n  symbol.describe FILE ID_OR_NAME\n  symbol.edit-context FILE ID_OR_NAME\n  symbol.references FILE ID_OR_NAME\n  type.describe FILE ID_OR_NAME\n  patch.validate FILE PATCH.json\n  patch.apply FILE PATCH.json\n\nExternal module commands:\n  interop.inspect MANIFEST.json\n  interop.call MANIFEST.json EXPORT ARGUMENTS.json [--timeout-ms N]\n               [--allow-effect NAME] [--allow-capability NAME]\n  external.summary MANIFEST.json\n  external.describe MANIFEST.json EXPORT\n  external.call-context MANIFEST.json EXPORT\n\nGlobal options:\n  -h, --help                Show this help\n  -V, --version             Show the CLI version\n\nJSON diagnostics conform to protocol/schema/diagnostics-v1.schema.json.", env!("CARGO_PKG_VERSION"));
}
