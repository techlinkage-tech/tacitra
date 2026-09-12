fn solve_085(value: i64) -> i64 {
    let offset = 3;
    step_085(value) + offset
}

fn main() {
    println!("{}", solve_085(115));
}
