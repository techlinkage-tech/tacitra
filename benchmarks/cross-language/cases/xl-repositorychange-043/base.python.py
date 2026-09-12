def solve_043(value: int, limit: int) -> int:
    return value - 5 if value > limit else 0

def main() -> int:
    return solve_043(63, 63)


if __name__ == "__main__":
    print(main())
