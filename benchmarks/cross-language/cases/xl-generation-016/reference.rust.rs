fn step_016(value: i64) -> i64 { value * 2 }

fn solve_016(value: i64) -> i64 { step_016(value) + 4 }

fn main() {
    println!("{}", solve_016(21));
}
