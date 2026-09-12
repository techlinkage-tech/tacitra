struct Packet012 { value: i64, enabled: bool }

fn solve_012(packet: Packet012) -> i64 {
    if packet.enabled { packet.value + 7 } else { packet.value }
}

fn main() {
    println!("{}", solve_012(Packet012 { value: 17, enabled: true }));
}
