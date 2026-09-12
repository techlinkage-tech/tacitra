def solve_006(value: int, limit: int) -> int:
    return 11 if value <= limit else 8

def main() -> int:
    return solve_006(8999999999999999994, 8999999999999999994)


if __name__ == "__main__":
    print(main())
