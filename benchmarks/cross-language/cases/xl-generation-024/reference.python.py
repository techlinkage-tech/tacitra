def step_024(value: int) -> int:
    return value * 2


def solve_024(value: int) -> int:
    return step_024(value) + 5

def main() -> int:
    return solve_024(29)


if __name__ == "__main__":
    print(main())
