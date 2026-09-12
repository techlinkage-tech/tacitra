fn solve_073(value: i64) -> i64 {
    let offset = 3;
    step_073(value) + offset
}

fn main() {
    println!("{}", solve_073(103));
}
