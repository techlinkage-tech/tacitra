fn solve_077(value: i64) -> i64 {
    let offset = 7;
    step_077(value) + offset
}

fn main() {
    println!("{}", solve_077(107));
}
