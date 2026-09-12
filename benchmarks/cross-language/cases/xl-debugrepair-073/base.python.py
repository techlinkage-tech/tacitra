def solve_073(value: int) -> int:
    offset = 3
    return step_073(value) + offset

def main() -> int:
    return solve_073(103)


if __name__ == "__main__":
    print(main())
