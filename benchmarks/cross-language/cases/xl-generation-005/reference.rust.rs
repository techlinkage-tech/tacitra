fn solve_005(value: i64, divisor: i64) -> Result<i64, &'static str> {
    if divisor == 0 { Err("zero") } else { Ok(value / divisor) }
}

fn consume(result: Result<i64, &'static str>) -> i64 {
    match result { Ok(value) => value, Err(_) => -1 }
}

fn main() {
    println!("{}", consume(solve_005(70, 7)));
}
