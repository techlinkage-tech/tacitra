def solve_022(value: int, limit: int) -> int:
    return 27 if value <= limit else 3

def main() -> int:
    return solve_022(8999999999999999978, 8999999999999999978)


if __name__ == "__main__":
    print(main())
