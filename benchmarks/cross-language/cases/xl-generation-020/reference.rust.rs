struct Packet020 { value: i64, enabled: bool }

fn solve_020(packet: Packet020) -> i64 {
    if packet.enabled { packet.value + 8 } else { packet.value }
}

fn main() {
    println!("{}", solve_020(Packet020 { value: 25, enabled: true }));
}
