fn solve_037(value: i64, limit: i64) -> i64 {
    if value > limit { value - 4 } else { 0 }
}

fn main() {
    println!("{}", solve_037(57, 57));
}
