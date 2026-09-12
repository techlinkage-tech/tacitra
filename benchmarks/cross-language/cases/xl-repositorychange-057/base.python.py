class Packet057:
    def __init__(self, value: int, enabled: bool):
        self.value = value
        self.enabled = enabled


def solve_057(packet: Packet057) -> int:
    return packet.value - 4 if packet.enabled else packet.value

def main() -> int:
    return solve_057(Packet057(77, True))


if __name__ == "__main__":
    print(main())
