import unittest

from shared.question_examples import QuestionConfigDtoExamples


class TestQuestionExamples(unittest.TestCase):
    def test_examples_include_c_and_cpp_catch2_examples(self):
        examples_by_language = {
            example.programmingLanguage: example
            for example in QuestionConfigDtoExamples()
        }

        self.assertIn("c", examples_by_language)
        self.assertIn("cpp", examples_by_language)
        self.assertIn("int add", examples_by_language["c"].indication)
        self.assertIn("TEST_CASE", examples_by_language["c"].validation)
        self.assertIn("std::string greet", examples_by_language["cpp"].indication)
        self.assertIn("TEST_CASE", examples_by_language["cpp"].validation)
