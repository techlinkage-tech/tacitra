def solve_031(value: int, limit: int) -> int:
    return value - 3 if value > limit else 0

def main() -> int:
    return solve_031(51, 51)


if __name__ == "__main__":
    print(main())
