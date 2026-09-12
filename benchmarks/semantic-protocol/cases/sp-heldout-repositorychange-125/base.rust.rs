fn unrelated_alpha(value: i64) -> i64 { value * 2 }
fn unrelated_beta(value: i64) -> i64 { value - 3 }
fn unrelated_gamma(enabled: bool) -> i64 { if enabled { 7 } else { 9 } }

fn solve_sp_125(value: i64, limit: i64) -> i64 { if value >= limit { 0 } else { value + 2 } }

fn main() { println!("{}", solve_sp_125(155, 155)); }
