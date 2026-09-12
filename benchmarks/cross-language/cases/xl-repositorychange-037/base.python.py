def solve_037(value: int, limit: int) -> int:
    return value - 4 if value > limit else 0

def main() -> int:
    return solve_037(57, 57)


if __name__ == "__main__":
    print(main())
