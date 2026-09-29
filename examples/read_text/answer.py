def read_lines(filename: str) -> list[str]:
    with open(filename, "r", encoding="utf-8") as source:
        return source.read().splitlines()
