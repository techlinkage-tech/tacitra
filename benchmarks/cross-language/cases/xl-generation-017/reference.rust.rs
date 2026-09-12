fn solve_017(value: i64, enabled: bool) -> i64 {
    if enabled { value + 5 } else { value - 5 }
}

fn main() {
    println!("{}", solve_017(22, true));
}
