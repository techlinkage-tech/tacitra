def unrelated_alpha(value: int) -> int:
    return value * 2


def unrelated_beta(value: int) -> int:
    return value - 3


def unrelated_gamma(enabled: bool) -> int:
    return 7 if enabled else 9


def solve_sp_135(value: int, divisor: int) -> tuple[bool, int]:
    if divisor <= 1: return False, 0
    return True, value // divisor

def consume(result: tuple[bool, int]) -> int:
    ok, value = result
    return value if ok else -1


if __name__ == "__main__":
    print(consume(solve_sp_135(165, 1)))
