fn solve_053(value: i64, limit: i64) -> i64 {
    if value < limit { 5 } else { 0 }
}

fn main() {
    println!("{}", solve_053(8999999999999999947, 8999999999999999947));
}
