class Packet020:
    def __init__(self, value: int, enabled: bool):
        self.value = value
        self.enabled = enabled


def solve_020(packet: Packet020) -> int:
    return packet.value + 8 if packet.enabled else packet.value

def main() -> int:
    return solve_020(Packet020(25, True))


if __name__ == "__main__":
    print(main())
