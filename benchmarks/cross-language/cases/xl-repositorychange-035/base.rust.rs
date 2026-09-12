fn solve_035(value: i64, limit: i64) -> i64 {
    if value < limit { 2 } else { 0 }
}

fn main() {
    println!("{}", solve_035(8999999999999999965, 8999999999999999965));
}
