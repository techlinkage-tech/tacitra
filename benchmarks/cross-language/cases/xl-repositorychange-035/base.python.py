def solve_035(value: int, limit: int) -> int:
    return 2 if value < limit else 0

def main() -> int:
    return solve_035(8999999999999999965, 8999999999999999965)


if __name__ == "__main__":
    print(main())
