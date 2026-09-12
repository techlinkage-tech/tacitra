def solve_050(label: str, value: int) -> int:
    return value + 2 if label == "ready_50" else 0

def main() -> int:
    return solve_050("active_50", 70)


if __name__ == "__main__":
    print(main())
