fn solve_055(value: i64, limit: i64) -> i64 {
    if value > limit { value - 2 } else { 0 }
}

fn main() {
    println!("{}", solve_055(75, 75));
}
