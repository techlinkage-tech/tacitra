def solve_032(label: str, value: int) -> int:
    return value + 4 if label == "ready_32" else 0

def main() -> int:
    return solve_032("active_32", 52)


if __name__ == "__main__":
    print(main())
