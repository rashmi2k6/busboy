from __future__ import annotations

import datetime as dt
import rlcompleter
import time
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from itertools import chain, filterfalse, groupby, islice, repeat, tee, zip_longest
from operator import itemgetter
from typing import (
    Callable,
    Dict,
    Generator,
    Generic,
    Iterable,
    Iterator,
    List,
    NoReturn,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from busboy.util.typevars import *


def swap(t: Tuple[A, B]) -> Tuple[B, A]:
    return (t[1], t[0])


def omap(f: Callable[[A], B], x: Optional[A]) -> Optional[B]:
    return None if x is None else f(x)


def oget(x: Optional[A], a: A) -> A:
    return a if x is None else x


def pairwise(xs: Iterable[A]) -> Iterable[Tuple[A, A]]:
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(xs)
    next(b, None)
    return zip(a, b)


def sliding_window(size: int, xs: Iterable[A]) -> Iterator[Tuple[A, ...]]:
    """A sliding window across the iterable xs.

    sliding_window(3, [1,2,3,4,5]) -> ((1,2,3), (2,3,4), (3,4,5))
    """
    return zip(*(drop(i, ys) for i, ys in enumerate(tee(xs, size))))


def tuplewise_padded(
    n: int, xs: Iterable[A], pad_value: B = None
) -> Iterator[Tuple[Union[A, B], ...]]:
    start_padding, end_padding = tee(repeat(pad_value, n - 1))
    return sliding_window(n, chain(start_padding, xs, end_padding))


def take(n: int, iterable: Iterable[A]) -> Iterable[A]:
    """Take the first n items of an iterable"""
    return islice(iterable, n)


def index(n: int, xs: Iterable[A]) -> Maybe[A]:
    """Get the item at index n in the iterable, if it exists."""
    return first(drop(n, xs))


def first(xs: Iterable[A]) -> Maybe[A]:
    """Take the first item of an iterable, if it exists."""
    try:
        return Just(list(take(1, xs))[0])
    except IndexError:
        return Nothing()


def drop(n: int, iterable: Iterable[A]) -> Iterable[A]:
    """Skip the first n items of an iterable"""
    return islice(iterable, n, None)


def unique(
    iterable: Iterable[A], key: Optional[Callable[[A], B]] = None
) -> Iterable[A]:
    "List unique elements, preserving order. Remember all elements ever seen."
    # unique_everseen('AAAABBBCCDAABBB') --> A B C D
    # unique_everseen('ABBCcAD', str.lower) --> A B C D
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element


def unique_justseen(iterable: Iterable[A], key=None) -> Iterable[A]:
    "List unique elements, preserving order. Remember only the element just seen."
    # unique_justseen('AAAABBBCCDAABBB') --> A B C D A B
    # unique_justseen('ABBCcAD', str.lower) --> A B C A D
    return map(next, map(itemgetter(1), groupby(iterable, key)))


def iterate(f: Callable[[A], A], a: A) -> Generator[A, None, NoReturn]:
    while True:
        a = f(a)
        yield a


def interval(i: float) -> Generator[dt.datetime, None, NoReturn]:
    while True:
        t1 = dt.datetime.now()
        yield t1
        t2 = dt.datetime.now()
        wait = i - (t2 - t1).total_seconds()
        if wait > 0:
            time.sleep(wait)


def combine_dictionaries(xs: Dict[A, B], ys: Dict[A, B]) -> Dict[A, List[B]]:
    zs: Dict[A, List[B]] = defaultdict(list)
    for k, v in chain(xs.items(), ys.items()):
        zs[k].append(v)
    return zs


def dict_collect_list(xs: Iterable[A], key: Callable[[A], B]) -> Dict[B, List[A]]:
    return dict_collect(xs, key, lambda xs, x: xs.append(x), list)


def dict_collect_set(xs: Iterable[A], key: Callable[[A], B]) -> Dict[B, Set[A]]:
    return dict_collect(xs, key, lambda xs, x: xs.add(x), set)


def dict_collect(
    xs: Iterable[A],
    key: Callable[[A], B],
    join: Callable[[C, A], None],
    empty: Callable[[], C],
) -> Dict[B, C]:
    output: Dict[B, C] = defaultdict(empty)
    for x in xs:
        join(output[key(x)], x)
    return dict(output)


class Maybe(Generic[A]):
    def __iter__(self) -> Iterator[A]:
        if isinstance(self, Just):
            return iter([self.value])
        else:
            return iter([])

    def map(self, f: Callable[[A], B]) -> Maybe[B]:
        if isinstance(self, Just):
            return Just(f(self.value))
        else:
            return cast(Maybe[B], self)

    def bind(self, f: Callable[[A], Maybe[B]]) -> Maybe[B]:
        if isinstance(self, Just):
            return f(self.value)
        else:
            return cast(Maybe[B], self)

    def bind_optional(self, f: Callable[[A], Optional[B]]) -> Maybe[B]:
        return self.bind(lambda a: Maybe.of(f(a)))

    def lift(self, f: Callable[[A, B], C], b: Maybe[B]) -> Maybe[C]:
        return b.ap(self.map(lambda a: partial(f, a)))

    def ap(self, f: Maybe[Callable[[A], B]]) -> Maybe[B]:
        return self.bind(lambda a: f.map(lambda g: g(a)))

    @staticmethod
    def of(x: Optional[A]) -> Maybe[A]:
        if x is None:
            return Nothing()
        else:
            return Just(x)

    def or_else(self, default: B) -> Union[A, B]:
        if isinstance(self, Just):
            return self.value
        else:
            return default

    def or_else_lazy(self, default: Callable[[], B]) -> Union[A, B]:
        if isinstance(self, Just):
            return self.value
        else:
            return default()

    def optional(self) -> Optional[A]:
        return self.or_else(None)

    def either(self, default: E) -> Either[E, A]:
        if isinstance(self, Just):
            return Right(self.value)
        else:
            return Left(default)

    def is_just(self) -> bool:
        return isinstance(self, Just)

    def is_nothing(self) -> bool:
        return isinstance(self, Nothing)

    @staticmethod
    def justs(ms: Iterable[Maybe[A]]) -> Iterable[A]:
        for m in ms:
            if isinstance(m, Just):
                yield m.value


@dataclass(frozen=True, order=True)
class Just(Maybe[A]):
    value: A


@dataclass(frozen=True, order=True)
class Nothing(Maybe[A]):
    pass


class Either(Generic[E, A]):
    def map(self, f: Callable[[A], B]) -> Either[E, B]:
        if isinstance(self, Right):
            return Right(f(self.value))
        else:
            return cast(Either[E, B], self)

    def bind(self, f: Callable[[A], Either[E, B]]) -> Either[E, B]:
        if isinstance(self, Right):
            return f(self.value)
        else:
            return cast(Either[E, B], self)

    def ap(self, f: Either[E, Callable[[A], B]]) -> Either[E, B]:
        if isinstance(self, Right) and isinstance(f, Right):
            return f.value(self.value)
        elif isinstance(f, Left):
            return f
        else:
            return cast(Either[E, B], self)


@dataclass(frozen=True)
class Right(Either[E, A]):
    value: A


@dataclass(frozen=True)
class Left(Either[E, A]):
    value: E
