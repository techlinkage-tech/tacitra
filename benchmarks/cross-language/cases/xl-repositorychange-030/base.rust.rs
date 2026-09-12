fn step_030(value: i64) -> i64 { value * 2 }

fn solve_030(value: i64) -> i64 { step_030(value) + 2 }

fn main() {
    println!("{}", solve_030(50));
}
