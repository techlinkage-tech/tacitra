def solve_065(value: int) -> int:
    offset = 7
    return step_065(value) + offset

def main() -> int:
    return solve_065(95)


if __name__ == "__main__":
    print(main())
