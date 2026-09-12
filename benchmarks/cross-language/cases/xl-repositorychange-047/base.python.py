def solve_047(value: int, limit: int) -> int:
    return 4 if value < limit else 0

def main() -> int:
    return solve_047(8999999999999999953, 8999999999999999953)


if __name__ == "__main__":
    print(main())
