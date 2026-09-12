fn solve_050(label: &str, value: i64) -> i64 {
    if label == "ready_50" { value + 2 } else { 0 }
}

fn main() {
    println!("{}", solve_050("active_50", 70));
}
