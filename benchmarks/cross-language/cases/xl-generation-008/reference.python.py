def step_008(value: int) -> int:
    return value * 2


def solve_008(value: int) -> int:
    return step_008(value) + 3

def main() -> int:
    return solve_008(13)


if __name__ == "__main__":
    print(main())
