from typing import NamedTuple
from unittest import TestCase

from holdings.positions.unique import Unique, UniqueList


class TestUnique(Unique):
    def __init__(self, a: int, b: int) -> None:
        self.a = a
        self.b = b

    class Key(NamedTuple):
        a: int
        b: int

    def key(self) -> "TestUnique.Key":
        return self.Key(self.a, self.b)


class UniqueListTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.list = UniqueList[TestUnique]([])


class AppendTests(UniqueListTestCase):
    def test(self) -> None:
        self.assertEqual(True, self.list.append(TestUnique(1, 1)))
        self.assertEqual(False, self.list.append(TestUnique(1, 1)))


class GetItemTests(UniqueListTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.list.append(TestUnique(1, 1))
        self.list.append(TestUnique(2, 2))
        self.list.append(TestUnique(3, 3))

    def test_index(self) -> None:
        self.assertEqual(TestUnique.Key(1, 1), self.list[0].key())

    def test_slice(self) -> None:
        self.assertEqual(
            [
                TestUnique.Key(1, 1),
                TestUnique.Key(2, 2),
            ],
            [u.key() for u in self.list[0:2]],
        )
