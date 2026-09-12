fn solve_022(value: i64, limit: i64) -> i64 {
    if value <= limit { 27 } else { 3 }
}

fn main() {
    println!("{}", solve_022(8999999999999999978, 8999999999999999978));
}
