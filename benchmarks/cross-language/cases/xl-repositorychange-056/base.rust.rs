fn solve_056(label: &str, value: i64) -> i64 {
    if label == "ready_56" { value + 3 } else { 0 }
}

fn main() {
    println!("{}", solve_056("active_56", 76));
}
