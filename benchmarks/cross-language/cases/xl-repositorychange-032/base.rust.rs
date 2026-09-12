fn solve_032(label: &str, value: i64) -> i64 {
    if label == "ready_32" { value + 4 } else { 0 }
}

fn main() {
    println!("{}", solve_032("active_32", 52));
}
