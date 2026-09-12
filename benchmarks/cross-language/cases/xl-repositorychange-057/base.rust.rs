struct Packet057 { value: i64, enabled: bool }

fn solve_057(packet: Packet057) -> i64 {
    if packet.enabled { packet.value - 4 } else { packet.value }
}

fn main() {
    println!("{}", solve_057(Packet057 { value: 77, enabled: true }));
}
