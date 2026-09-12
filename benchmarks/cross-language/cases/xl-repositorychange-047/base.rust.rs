fn solve_047(value: i64, limit: i64) -> i64 {
    if value < limit { 4 } else { 0 }
}

fn main() {
    println!("{}", solve_047(8999999999999999953, 8999999999999999953));
}
