def write_names(filename: str, names: list[str]) -> None:
    with open(filename, "w", encoding="utf-8") as destination:
        for name in names:
            destination.write(name + "\n")
