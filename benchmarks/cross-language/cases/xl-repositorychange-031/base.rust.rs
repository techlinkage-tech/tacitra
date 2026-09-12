fn solve_031(value: i64, limit: i64) -> i64 {
    if value > limit { value - 3 } else { 0 }
}

fn main() {
    println!("{}", solve_031(51, 51));
}
