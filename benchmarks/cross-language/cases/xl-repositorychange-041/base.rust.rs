fn solve_041(value: i64, limit: i64) -> i64 {
    if value < limit { 3 } else { 0 }
}

fn main() {
    println!("{}", solve_041(8999999999999999959, 8999999999999999959));
}
