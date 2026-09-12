fn solve_043(value: i64, limit: i64) -> i64 {
    if value > limit { value - 5 } else { 0 }
}

fn main() {
    println!("{}", solve_043(63, 63));
}
