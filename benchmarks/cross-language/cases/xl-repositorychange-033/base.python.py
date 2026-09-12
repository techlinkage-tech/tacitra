class Packet033:
    def __init__(self, value: int, enabled: bool):
        self.value = value
        self.enabled = enabled


def solve_033(packet: Packet033) -> int:
    return packet.value - 5 if packet.enabled else packet.value

def main() -> int:
    return solve_033(Packet033(53, True))


if __name__ == "__main__":
    print(main())
