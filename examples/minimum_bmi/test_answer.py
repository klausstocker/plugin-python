"""Unit tests for the minimum BMI example.

Run from this directory with:
    python -m unittest test_answer.py

Or run from the repository root with:
    python -m unittest discover -s examples/minimum_bmi -p "test_*.py"
"""

import unittest

import answer


def correct_implementation(people):
    """Return the name of the person with the lowest BMI."""
    if not people:
        return None

    person_with_lowest_bmi = min(
        people,
        key=lambda person: person[1] / person[2] ** 2,
    )
    return person_with_lowest_bmi[0]


class Checker(unittest.TestCase):  # do not rename; plugin checks expect this name
    def test_returns_name_with_minimum_bmi(self):
        test_people = [
            ("Mia", 64.0, 1.70),
            ("Noah", 81.0, 1.90),
            ("Lena", 59.0, 1.74),
            ("Omar", 75.0, 1.78),
        ]

        self.assertEqual(
            answer.person_with_minimum_bmi(test_people),
            correct_implementation(test_people),
        )

    def test_uses_test_data_not_example_data(self):
        test_people = [
            ("Chris", 82.0, 1.78),
            ("Riley", 54.0, 1.68),
            ("Jordan", 98.0, 2.05),
        ]

        self.assertNotEqual(test_people, answer.EXAMPLE_PEOPLE)
        self.assertEqual(answer.person_with_minimum_bmi(test_people), "Riley")

    def test_empty_list_returns_none(self):
        self.assertIsNone(answer.person_with_minimum_bmi([]))
