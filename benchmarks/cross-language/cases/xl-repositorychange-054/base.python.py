def step_054(value: int) -> int:
    return value * 6


def solve_054(value: int) -> int:
    return step_054(value) + 6

def main() -> int:
    return solve_054(74)


if __name__ == "__main__":
    print(main())
