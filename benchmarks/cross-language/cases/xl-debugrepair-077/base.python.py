def solve_077(value: int) -> int:
    offset = 7
    return step_077(value) + offset

def main() -> int:
    return solve_077(107)


if __name__ == "__main__":
    print(main())
