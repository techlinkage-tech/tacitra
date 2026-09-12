def solve_061(value: int) -> int:
    offset = 3
    return step_061(value) + offset

def main() -> int:
    return solve_061(91)


if __name__ == "__main__":
    print(main())
