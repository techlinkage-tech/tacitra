def solve_040(value: int, divisor: int) -> tuple[bool, int]:
    if divisor <= 1:
        return False, 0
    return True, value // divisor


def consume(result: tuple[bool, int]) -> int:
    ok, value = result
    return value if ok else -1

def main() -> int:
    return consume(solve_040(60, 1))


if __name__ == "__main__":
    print(main())
