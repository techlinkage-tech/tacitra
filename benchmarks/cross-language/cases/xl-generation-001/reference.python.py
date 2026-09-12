def solve_001(value: int, enabled: bool) -> int:
    if enabled:
        return value + 3
    return value - 3

def main() -> int:
    return solve_001(6, True)


if __name__ == "__main__":
    print(main())
