fn solve_081(value: i64) -> i64 {
    let offset = 5;
    step_081(value) + offset
}

fn main() {
    println!("{}", solve_081(111));
}
