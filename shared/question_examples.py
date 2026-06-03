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
import answer

class Checker(unittest.TestCase): # do not rename
    def test_return(self): # test method names must start with 'test_'
        args = (1, 2)
        student_result = answer.calculate_sum(*args) # call to students implementation
        expected_result = correctImplementation(*args)
        self.assertEqual(student_result, expected_result)

    def test_output(self):
        args = (3, 4)
        with RedirectedStdout() as student_out:
            answer.calculate_sum(*args)
        with RedirectedStdout() as expected_out:
            correctImplementation(*args)
        self.assertEqual(str(student_out), str(expected_out))
""",
        linterConfig="--disable=C0114,C0115,C0116"),
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
import answer

class Checker(unittest.TestCase): # do not rename
    def test_example(self): # test method names must start with test_
        rotations = ["L68", "L30", "R48", "L5", "R60", "L55", "L1", "L99", "R14", "L82"]
        #self.assertEqual(count_zero_stops(50, rotations), 3)
        self.assertEqual(answer.countPointingAt0(50, rotations), 3)

    def test_wraparound(self):
        #self.assertEqual(count_zero_stops(5, ["L10", "R5"]), 1)
        self.assertEqual(answer.countPointingAt0(5, ["L10", "R5"]), 1)

    def test_two_zero_stops(self):
        rotations = ["R50", "L1", "R1"]
        #self.assertEqual(count_zero_stops(50, rotations), 2)
        self.assertEqual(answer.countPointingAt0(50, rotations), 2)

    def test_five_zero_stops(self):
        rotations = ["R50", "R100", "L100", "R200", "L300"]
        #self.assertEqual(count_zero_stops(50, rotations), 5)
        self.assertEqual(answer.countPointingAt0(50, rotations), 5)

""",
        linterConfig="--disable=C0114,C0115,C0116"),
    QuestionConfigDto(
        indication="""
def count_larger_mean(values: list[float]):
    if not values:
        return 0
    mean = sum(values) / len(values)
    count = 0
    for v in values:
        count += 1 if v > mean else 0
    return count
""",
        validation="""
import unittest
import answer

class Checker(unittest.TestCase): # do not rename
    def test_return(self): # test method names must start with 'test_'
        self.assertEqual(answer.count_larger_mean([]), 0)
        self.assertEqual(answer.count_larger_mean([0, 1]), 1)
        self.assertEqual(answer.count_larger_mean([0, 0, 1]), 1)
        self.assertEqual(answer.count_larger_mean([0, 2, 4]), 1)
        self.assertEqual(answer.count_larger_mean([0, 1, 1]), 2)

""",
        linterConfig="--disable=C0114,C0115,C0116"),
    QuestionConfigDto(
        indication="""
import sys
import math

def minimalDistance(points: list[tuple[float,float]]):
    if not points:
        return None

    min_dist = sys.float_info.max

    for p1 in points:
        for p2 in points:
            dist = math.sqrt((p2[0] - p1[1]) ** 2 + (p2[1] - p1[1]) ** 2)
            min_dist = min(min_dist, dist)
    return min_dist

""",
        validation="""
import unittest
import answer
import random
import sys
import math

def correctImplementation(points: list[tuple[float,float]]):
    if not points:
        return None

    min_dist = sys.float_info.max

    for p1 in points:
        for p2 in points:
            dist = math.sqrt((p2[0] - p1[1]) ** 2 + (p2[1] - p1[1]) ** 2)
            min_dist = min(min_dist, dist)
    return min_dist

class Checker(unittest.TestCase): # do not rename
    def test_return(self): # test method names must start with 'test_'
        points = []
        for _ in range(10):
            points.append((random.random() * 10., random.random() * 10.))
        self.assertAlmostEqual(answer.minimalDistance(points), correctImplementation(points))

""",
        linterConfig="--disable=C0114,C0115,C0116")
    ,
    QuestionConfigDto(
        indication="""
def rad2degree(angle_rad: float):
    grad = 0
    minuten = 0
    sekunden = 0
    quadrant = 1
    return grad, minuten, sekunden, quadrant

""",
        validation="""
import math
import unittest
import answer

def correct_implementation(rad: float):
    grad_gesamt = math.degrees(rad)

    while grad_gesamt < 0:
        grad_gesamt += 360.

    grad = int(grad_gesamt)
    rest = abs(grad_gesamt - grad) * 60

    minuten = int(rest)
    sekunden = (rest - minuten) * 60

    grad_norm = grad % 360
    quadrant = 0
    if 0 <= grad_norm < 90:
        quadrant = 1
    elif 90 <= grad_norm < 180:
        quadrant = 2
    elif 180 <= grad_norm < 270:
        quadrant = 3
    elif 270 <= grad_norm < 360:
        quadrant = 4

    return grad, minuten, sekunden, quadrant

class Checker(unittest.TestCase): # do not rename
    def test_zero(self): # test method names must start with 'test_'
        for a in range(-365, 400, 45):
            self.assertEqual(answer.rad2degree(a), correct_implementation(a))

""",
        linterConfig="--disable=C0114,C0115,C0116")
    ]


def QuestionConfigDtoExamplesWorkingIndication():
    ex = QuestionConfigDtoExamples()
    return [ex[0], ex[2], ex[3]]
