def unrelated_alpha(value: int) -> int:
    return value * 2


def unrelated_beta(value: int) -> int:
    return value - 3


def unrelated_gamma(enabled: bool) -> int:
    return 7 if enabled else 9


class PacketSp138:
    def __init__(self, value: int, enabled: bool):
        self.value = value
        self.enabled = enabled

def solve_sp_138(packet: PacketSp138) -> int:
    return packet.value + 3 if packet.enabled else packet.value


if __name__ == "__main__":
    print(solve_sp_138(PacketSp138(168, True)))
