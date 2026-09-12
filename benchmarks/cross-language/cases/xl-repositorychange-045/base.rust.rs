struct Packet045 { value: i64, enabled: bool }

fn solve_045(packet: Packet045) -> i64 {
    if packet.enabled { packet.value - 2 } else { packet.value }
}

fn main() {
    println!("{}", solve_045(Packet045 { value: 65, enabled: true }));
}
