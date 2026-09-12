def solve_038(label: str, value: int) -> int:
    return value + 5 if label == "ready_38" else 0

def main() -> int:
    return solve_038("active_38", 58)


if __name__ == "__main__":
    print(main())
