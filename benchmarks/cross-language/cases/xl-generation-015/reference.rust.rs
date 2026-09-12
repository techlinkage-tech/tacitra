fn solve_015(left: i64, right: i64, enabled: bool) -> i64 {
    if enabled && left > 0 { left + right } else { 0 }
}

fn main() {
    println!("{}", solve_015(20, 3, true));
}
