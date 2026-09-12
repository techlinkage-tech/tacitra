fn solve_014(value: i64, limit: i64) -> i64 {
    if value <= limit { 19 } else { 2 }
}

fn main() {
    println!("{}", solve_014(8999999999999999986, 8999999999999999986));
}
