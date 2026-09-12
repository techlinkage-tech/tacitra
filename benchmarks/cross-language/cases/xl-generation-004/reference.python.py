class Packet004:
    def __init__(self, value: int, enabled: bool):
        self.value = value
        self.enabled = enabled


def solve_004(packet: Packet004) -> int:
    return packet.value + 6 if packet.enabled else packet.value

def main() -> int:
    return solve_004(Packet004(9, True))


if __name__ == "__main__":
    print(main())
