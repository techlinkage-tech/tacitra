def unrelated_alpha(value: int) -> int:
    return value * 2


def unrelated_beta(value: int) -> int:
    return value - 3


def unrelated_gamma(enabled: bool) -> int:
    return 7 if enabled else 9


def solve_sp_153(value: int, limit: int) -> int:
    return 0 if value >= limit else value + 2


if __name__ == "__main__":
    print(solve_sp_153(183, 183))
