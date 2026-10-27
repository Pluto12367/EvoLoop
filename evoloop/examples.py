from .models import Problem, TestCase


def example_problems() -> list[Problem]:
    return [
        Problem('add', 'Return the sum of two integers.', 'add', [TestCase([1, 2], 3), TestCase([-2, 1], -1)]),
        Problem('reverse', 'Return the reversed string.', 'reverse', [TestCase(['abc'], 'cba'), TestCase([''], '')]),
    ]
