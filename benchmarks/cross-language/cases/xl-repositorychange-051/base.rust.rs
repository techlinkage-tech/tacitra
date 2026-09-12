struct Packet051 { value: i64, enabled: bool }

fn solve_051(packet: Packet051) -> i64 {
    if packet.enabled { packet.value - 3 } else { packet.value }
}

fn main() {
    println!("{}", solve_051(Packet051 { value: 71, enabled: true }));
}
