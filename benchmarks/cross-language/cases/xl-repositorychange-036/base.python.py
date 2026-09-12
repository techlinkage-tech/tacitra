def step_036(value: int) -> int:
    return value * 3


def solve_036(value: int) -> int:
    return step_036(value) + 3

def main() -> int:
    return solve_036(56)


if __name__ == "__main__":
    print(main())
