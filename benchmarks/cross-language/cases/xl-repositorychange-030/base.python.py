def step_030(value: int) -> int:
    return value * 2


def solve_030(value: int) -> int:
    return step_030(value) + 2

def main() -> int:
    return solve_030(50)


if __name__ == "__main__":
    print(main())
