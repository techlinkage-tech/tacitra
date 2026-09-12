def solve_011(label: str) -> int:
    return 16 if label == "ready_11" else 6

def main() -> int:
    return solve_011("ready_11")


if __name__ == "__main__":
    print(main())
