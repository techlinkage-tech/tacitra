class Packet045:
    def __init__(self, value: int, enabled: bool):
        self.value = value
        self.enabled = enabled


def solve_045(packet: Packet045) -> int:
    return packet.value - 2 if packet.enabled else packet.value

def main() -> int:
    return solve_045(Packet045(65, True))


if __name__ == "__main__":
    print(main())
