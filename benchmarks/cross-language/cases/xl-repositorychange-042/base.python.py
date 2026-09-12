def step_042(value: int) -> int:
    return value * 4


def solve_042(value: int) -> int:
    return step_042(value) + 4

def main() -> int:
    return solve_042(62)


if __name__ == "__main__":
    print(main())
