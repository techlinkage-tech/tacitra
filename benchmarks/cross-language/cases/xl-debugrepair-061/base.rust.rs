fn solve_061(value: i64) -> i64 {
    let offset = 3;
    step_061(value) + offset
}

fn main() {
    println!("{}", solve_061(91));
}
