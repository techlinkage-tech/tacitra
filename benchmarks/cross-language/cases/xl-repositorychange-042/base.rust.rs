fn step_042(value: i64) -> i64 { value * 4 }

fn solve_042(value: i64) -> i64 { step_042(value) + 4 }

fn main() {
    println!("{}", solve_042(62));
}
