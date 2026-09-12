struct Packet033 { value: i64, enabled: bool }

fn solve_033(packet: Packet033) -> i64 {
    if packet.enabled { packet.value - 5 } else { packet.value }
}

fn main() {
    println!("{}", solve_033(Packet033 { value: 53, enabled: true }));
}
