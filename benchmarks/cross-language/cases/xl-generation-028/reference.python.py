class Packet028:
    def __init__(self, value: int, enabled: bool):
        self.value = value
        self.enabled = enabled


def solve_028(packet: Packet028) -> int:
    return packet.value + 2 if packet.enabled else packet.value

def main() -> int:
    return solve_028(Packet028(33, True))


if __name__ == "__main__":
    print(main())
