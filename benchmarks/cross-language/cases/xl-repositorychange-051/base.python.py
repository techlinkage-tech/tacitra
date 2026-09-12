class Packet051:
    def __init__(self, value: int, enabled: bool):
        self.value = value
        self.enabled = enabled


def solve_051(packet: Packet051) -> int:
    return packet.value - 3 if packet.enabled else packet.value

def main() -> int:
    return solve_051(Packet051(71, True))


if __name__ == "__main__":
    print(main())
