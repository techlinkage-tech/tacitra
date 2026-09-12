fn solve_009(value: i64, enabled: bool) -> i64 {
    if enabled { value + 4 } else { value - 4 }
}

fn main() {
    println!("{}", solve_009(14, true));
}
