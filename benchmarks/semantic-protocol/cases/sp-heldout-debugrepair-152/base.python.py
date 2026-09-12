def unrelated_alpha(value: int) -> int:
    return value * 2


def unrelated_beta(value: int) -> int:
    return value - 3


def unrelated_gamma(enabled: bool) -> int:
    return 7 if enabled else 9


def solve_sp_152(value: int) -> int:
    return value + 1


if __name__ == "__main__":
    print(solve_sp_152(182))
