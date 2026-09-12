def solve_017(value: int, enabled: bool) -> int:
    if enabled:
        return value + 5
    return value - 5

def main() -> int:
    return solve_017(22, True)


if __name__ == "__main__":
    print(main())
