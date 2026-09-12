def solve_007(left: int, right: int, enabled: bool) -> int:
    return left + right if enabled and left > 0 else 0

def main() -> int:
    return solve_007(12, 2, True)


if __name__ == "__main__":
    print(main())
