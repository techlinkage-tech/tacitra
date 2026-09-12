def solve_056(label: str, value: int) -> int:
    return value + 3 if label == "ready_56" else 0

def main() -> int:
    return solve_056("active_56", 76)


if __name__ == "__main__":
    print(main())
