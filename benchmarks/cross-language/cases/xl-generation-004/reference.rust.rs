struct Packet004 { value: i64, enabled: bool }

fn solve_004(packet: Packet004) -> i64 {
    if packet.enabled { packet.value + 6 } else { packet.value }
}

fn main() {
    println!("{}", solve_004(Packet004 { value: 9, enabled: true }));
}
