fn solve_044(label: &str, value: i64) -> i64 {
    if label == "ready_44" { value + 6 } else { 0 }
}

fn main() {
    println!("{}", solve_044("active_44", 64));
}
