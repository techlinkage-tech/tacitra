fn solve_049(value: i64, limit: i64) -> i64 {
    if value > limit { value - 6 } else { 0 }
}

fn main() {
    println!("{}", solve_049(69, 69));
}
