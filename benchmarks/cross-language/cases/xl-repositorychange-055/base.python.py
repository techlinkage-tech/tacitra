def solve_055(value: int, limit: int) -> int:
    return value - 2 if value > limit else 0

def main() -> int:
    return solve_055(75, 75)


if __name__ == "__main__":
    print(main())
