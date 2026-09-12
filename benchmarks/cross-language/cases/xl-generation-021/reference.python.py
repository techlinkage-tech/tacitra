def solve_021(value: int, divisor: int) -> tuple[bool, int]:
    if divisor == 0:
        return False, 0
    return True, value // divisor


def consume(result: tuple[bool, int]) -> int:
    ok, value = result
    return value if ok else -1

def main() -> int:
    return consume(solve_021(52, 2))


if __name__ == "__main__":
    print(main())
