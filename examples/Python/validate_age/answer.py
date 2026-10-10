def validate_age(age: int) -> int:
    if age < 0:
        raise ValueError("Age must not be negative")
    return age
