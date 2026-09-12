def solve_009(value: int, enabled: bool) -> int:
    if enabled:
        return value + 4
    return value - 4

def main() -> int:
    return solve_009(14, True)


if __name__ == "__main__":
    print(main())
