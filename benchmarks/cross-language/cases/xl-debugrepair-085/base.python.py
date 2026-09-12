def solve_085(value: int) -> int:
    offset = 3
    return step_085(value) + offset

def main() -> int:
    return solve_085(115)


if __name__ == "__main__":
    print(main())
