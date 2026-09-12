def unrelated_alpha(value: int) -> int:
    return value * 2


def unrelated_beta(value: int) -> int:
    return value - 3


def unrelated_gamma(enabled: bool) -> int:
    return 7 if enabled else 9


class PacketSp06:
    def __init__(self, value: int, enabled: bool):
        self.value = value
        self.enabled = enabled

def solve_sp_06(packet: PacketSp06) -> int:
    return packet.value + 3 if packet.enabled else packet.value


if __name__ == "__main__":
    print(solve_sp_06(PacketSp06(36, True)))
