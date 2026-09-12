fn solve_006(value: i64, limit: i64) -> i64 {
    if value <= limit { 11 } else { 8 }
}

fn main() {
    println!("{}", solve_006(8999999999999999994, 8999999999999999994));
}
