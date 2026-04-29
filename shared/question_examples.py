from shared.question_config import QuestionConfigDto

def QuestionConfigDtoExamples():
    return [QuestionConfigDto(
        indication="""
def calculate_sum(a, b):
    print('the sum is ' + str(a + b))
    return a + b
""",
        validation="""
def correctImplementation(arg1, arg2):
    sum = arg1 + arg2
    print(f'the sum is {sum}')
    return sum

import unittest

class Checker(unittest.TestCase): # do not rename
    def test_return(self): # test method names must start with 'test_'
        args = (1, 2)
        student_result = calculate_sum(*args) # call to students implementation
        expected_result = correctImplementation(*args)
        self.assertEqual(student_result, expected_result)

    def test_output(self):
        args = (3, 4)
        with RedirectedStdout() as student_out:
            calculate_sum(*args)
        with RedirectedStdout() as expected_out:
            correctImplementation(*args)
        self.assertEqual(str(student_out), str(expected_out))
"""
    ),
    QuestionConfigDto(
        indication="""
def countPointingAt0(start: int, rotations: list[str]):
    return 0
""",
        validation="""
# https://adventofcode.com/2025/day/1

from typing import Iterable

def count_zero_stops(start: int, rotations: Iterable[str]) -> int:
    if not 0 <= start <= 99:
        raise ValueError("start must be between 0 and 99")

    position = start
    zero_stops = 0

    for rotation in rotations:
        if not rotation:
            raise ValueError("rotation entries must be non-empty strings")

        direction = rotation[0]
        if direction not in {"L", "R"}:
            raise ValueError(f"invalid direction in rotation: {rotation}")

        distance_str = rotation[1:]
        if not distance_str.isdigit():
            raise ValueError(f"invalid distance in rotation: {rotation}")

        distance = int(distance_str)
        if direction == "L":
            position = (position - distance) % 100
        else:
            position = (position + distance) % 100

        if position == 0:
            zero_stops += 1

    return zero_stops

import unittest

class Checker(unittest.TestCase): # do not rename
    def test_example(self): # test method names must start with test_
        rotations = ["L68", "L30", "R48", "L5", "R60", "L55", "L1", "L99", "R14", "L82"]
        #self.assertEqual(count_zero_stops(50, rotations), 3)
        self.assertEqual(countPointingAt0(50, rotations), 3)

    def test_wraparound(self):
        #self.assertEqual(count_zero_stops(5, ["L10", "R5"]), 1)
        self.assertEqual(countPointingAt0(5, ["L10", "R5"]), 1)
        
    def test_two_zero_stops(self):
        rotations = ["R50", "L1", "R1"]
        #self.assertEqual(count_zero_stops(50, rotations), 2)
        self.assertEqual(countPointingAt0(50, rotations), 2)

    def test_five_zero_stops(self):
        rotations = ["R50", "R100", "L100", "R200", "L300"]
        #self.assertEqual(count_zero_stops(50, rotations), 5)
        self.assertEqual(countPointingAt0(50, rotations), 5)

"""
    )]