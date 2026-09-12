def solve_081(value: int) -> int:
    offset = 5
    return step_081(value) + offset

def main() -> int:
    return solve_081(111)


if __name__ == "__main__":
    print(main())
