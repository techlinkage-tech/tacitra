def solve_049(value: int, limit: int) -> int:
    return value - 6 if value > limit else 0

def main() -> int:
    return solve_049(69, 69)


if __name__ == "__main__":
    print(main())
