struct Packet028 { value: i64, enabled: bool }

fn solve_028(packet: Packet028) -> i64 {
    if packet.enabled { packet.value + 2 } else { packet.value }
}

fn main() {
    println!("{}", solve_028(Packet028 { value: 33, enabled: true }));
}
