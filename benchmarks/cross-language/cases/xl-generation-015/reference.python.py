def solve_015(left: int, right: int, enabled: bool) -> int:
    return left + right if enabled and left > 0 else 0

def main() -> int:
    return solve_015(20, 3, True)


if __name__ == "__main__":
    print(main())
