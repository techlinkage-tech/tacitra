def step_048(value: int) -> int:
    return value * 5


def solve_048(value: int) -> int:
    return step_048(value) + 5

def main() -> int:
    return solve_048(68)


if __name__ == "__main__":
    print(main())
