def step_016(value: int) -> int:
    return value * 2


def solve_016(value: int) -> int:
    return step_016(value) + 4

def main() -> int:
    return solve_016(21)


if __name__ == "__main__":
    print(main())
