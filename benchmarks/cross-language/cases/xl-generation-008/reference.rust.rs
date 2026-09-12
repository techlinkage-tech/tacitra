fn step_008(value: i64) -> i64 { value * 2 }

fn solve_008(value: i64) -> i64 { step_008(value) + 3 }

fn main() {
    println!("{}", solve_008(13));
}
