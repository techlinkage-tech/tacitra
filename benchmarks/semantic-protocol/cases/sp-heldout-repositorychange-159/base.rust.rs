fn unrelated_alpha(value: i64) -> i64 { value * 2 }
fn unrelated_beta(value: i64) -> i64 { value - 3 }
fn unrelated_gamma(enabled: bool) -> i64 { if enabled { 7 } else { 9 } }

fn solve_sp_159(value: i64, divisor: i64) -> Result<i64, &'static str> { if divisor <= 1 { Err("zero") } else { Ok(value / divisor) } }
fn consume(result: Result<i64, &'static str>) -> i64 { match result { Ok(value) => value, Err(_) => -1 } }

fn main() { println!("{}", consume(solve_sp_159(189, 1))); }
