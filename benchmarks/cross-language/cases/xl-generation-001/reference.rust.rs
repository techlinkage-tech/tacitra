fn solve_001(value: i64, enabled: bool) -> i64 {
    if enabled { value + 3 } else { value - 3 }
}

fn main() {
    println!("{}", solve_001(6, true));
}
