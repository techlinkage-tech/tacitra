def solve_025(value: int, enabled: bool) -> int:
    if enabled:
        return value + 6
    return value - 6

def main() -> int:
    return solve_025(30, True)


if __name__ == "__main__":
    print(main())
