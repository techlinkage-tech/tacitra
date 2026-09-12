def solve_014(value: int, limit: int) -> int:
    return 19 if value <= limit else 2

def main() -> int:
    return solve_014(8999999999999999986, 8999999999999999986)


if __name__ == "__main__":
    print(main())
