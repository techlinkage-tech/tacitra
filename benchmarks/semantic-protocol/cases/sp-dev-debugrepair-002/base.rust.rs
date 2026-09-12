fn unrelated_alpha(value: i64) -> i64 { value * 2 }
fn unrelated_beta(value: i64) -> i64 { value - 3 }
fn unrelated_gamma(enabled: bool) -> i64 { if enabled { 7 } else { 9 } }

struct PacketSp02 { value: i64, enabled: bool }

fn solve_sp_02(packet: PacketSp02) -> i64 { if packet.enabled { packet.value + 3 } else { packet.value } }

fn main() { println!("{}", solve_sp_02(PacketSp02 { value: 32, enabled: true })); }
