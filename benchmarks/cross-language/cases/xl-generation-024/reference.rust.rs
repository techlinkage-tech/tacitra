fn step_024(value: i64) -> i64 { value * 2 }

fn solve_024(value: i64) -> i64 { step_024(value) + 5 }

fn main() {
    println!("{}", solve_024(29));
}
