def solve_044(label: str, value: int) -> int:
    return value + 6 if label == "ready_44" else 0

def main() -> int:
    return solve_044("active_44", 64)


if __name__ == "__main__":
    print(main())
