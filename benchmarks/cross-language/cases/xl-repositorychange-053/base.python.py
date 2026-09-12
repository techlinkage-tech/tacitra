def solve_053(value: int, limit: int) -> int:
    return 5 if value < limit else 0

def main() -> int:
    return solve_053(8999999999999999947, 8999999999999999947)


if __name__ == "__main__":
    print(main())
