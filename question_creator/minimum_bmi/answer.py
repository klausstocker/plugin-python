"""Reference solution for the minimum BMI example."""

EXAMPLE_PEOPLE = [
    ("Alex", 72.0, 1.80),
    ("Sam", 68.0, 1.75),
    ("Taylor", 90.0, 1.95),
]


def person_with_minimum_bmi(people):
    """Return the name of the person with the lowest BMI.

    Each person is represented as a tuple containing:
    - name in position 0
    - weight in kilograms in position 1
    - height in meters in position 2
    """
    if not people:
        return None

    person_with_lowest_bmi = people[0]
    lowest_bmi = person_with_lowest_bmi[1] / person_with_lowest_bmi[2] ** 2

    for person in people[1:]:
        bmi = person[1] / person[2] ** 2
        if bmi < lowest_bmi:
            person_with_lowest_bmi = person
            lowest_bmi = bmi

    return person_with_lowest_bmi[0]
