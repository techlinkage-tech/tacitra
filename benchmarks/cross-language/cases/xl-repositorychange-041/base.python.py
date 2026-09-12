def solve_041(value: int, limit: int) -> int:
    return 3 if value < limit else 0

def main() -> int:
    return solve_041(8999999999999999959, 8999999999999999959)


if __name__ == "__main__":
    print(main())
