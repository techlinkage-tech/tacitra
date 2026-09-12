fn solve_025(value: i64, enabled: bool) -> i64 {
    if enabled { value + 6 } else { value - 6 }
}

fn main() {
    println!("{}", solve_025(30, true));
}
