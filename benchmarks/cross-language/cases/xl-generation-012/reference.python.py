class Packet012:
    def __init__(self, value: int, enabled: bool):
        self.value = value
        self.enabled = enabled


def solve_012(packet: Packet012) -> int:
    return packet.value + 7 if packet.enabled else packet.value

def main() -> int:
    return solve_012(Packet012(17, True))


if __name__ == "__main__":
    print(main())
