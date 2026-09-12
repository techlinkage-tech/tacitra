fn solve_038(label: &str, value: i64) -> i64 {
    if label == "ready_38" { value + 5 } else { 0 }
}

fn main() {
    println!("{}", solve_038("active_38", 58));
}
