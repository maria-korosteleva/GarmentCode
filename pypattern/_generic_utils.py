from typing import TypeVar, Generic, Sequence, Callable


# proper inserstions by key with bicest module in python <3.10
# https://stackoverflow.com/questions/27672494/how-to-use-bisect-insort-left-with-a-key

T = TypeVar('T')
V = TypeVar('V')

class KeyWrapper(Generic[T, V]):
    def __init__(self, iterable: Sequence[T], key: Callable[[T], V]):
        self.it = iterable
        self.key = key

    def __getitem__(self, i: int) -> V:
        return self.key(self.it[i])

    def __len__(self) -> int:
        return len(self.it)