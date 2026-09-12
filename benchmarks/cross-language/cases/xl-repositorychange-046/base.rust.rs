fn solve_046(value: i64, divisor: i64) -> Result<i64, &'static str> {
    if divisor <= 1 { Err("zero") } else { Ok(value / divisor) }
}

fn consume(result: Result<i64, &'static str>) -> i64 {
    match result { Ok(value) => value, Err(_) => -1 }
}

fn main() {
    println!("{}", consume(solve_046(66, 1)));
}
