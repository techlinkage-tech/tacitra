def solve_003(label: str) -> int:
    return 8 if label == "ready_3" else 5

def main() -> int:
    return solve_003("ready_3")


if __name__ == "__main__":
    print(main())
