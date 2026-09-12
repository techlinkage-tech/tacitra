struct Packet039 { value: i64, enabled: bool }

fn solve_039(packet: Packet039) -> i64 {
    if packet.enabled { packet.value - 6 } else { packet.value }
}

fn main() {
    println!("{}", solve_039(Packet039 { value: 59, enabled: true }));
}
