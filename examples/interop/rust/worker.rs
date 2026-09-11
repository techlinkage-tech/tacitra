use std::io::{self, Read};

fn number_after(source: &str, marker: &str) -> i64 {
    let tail = source.split_once(marker).expect("request field").1;
    tail.trim_start()
        .chars()
        .take_while(|character| character.is_ascii_digit() || *character == '-')
        .collect::<String>()
        .parse()
        .expect("integer parameter")
}

fn main() {
    let mut request = String::new();
    io::stdin().read_to_string(&mut request).expect("stdin");
    let left = number_after(&request, "\"left\":");
    let right = number_after(&request, "\"right\":");
    println!(
        "{{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{},\"meta\":{{\"effects\":[],\"capabilities\":[]}}}}",
        left + right
    );
}
