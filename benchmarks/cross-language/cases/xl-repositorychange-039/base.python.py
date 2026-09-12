class Packet039:
    def __init__(self, value: int, enabled: bool):
        self.value = value
        self.enabled = enabled


def solve_039(packet: Packet039) -> int:
    return packet.value - 6 if packet.enabled else packet.value

def main() -> int:
    return solve_039(Packet039(59, True))


if __name__ == "__main__":
    print(main())
