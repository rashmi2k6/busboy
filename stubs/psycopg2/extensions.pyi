from typing import *

class cursor:
    def __enter__(self, *args: Any) -> cursor: ...
    def __exit__(self, *args: Any) -> None: ...
    def mogrify(self, query: Union[str, bytes], items: Tuple[Any, ...]) -> bytes: ...
    def execute(self, query: Union[str, bytes], values: List[Any] = ...) -> None: ...
    def fetchall(self) -> Iterable[Tuple[Any, ...]]: ...
    def fetchone(self) -> Optional[Tuple[Any, ...]]: ...

_cursor = cursor

class connection:
    def __enter__(self, *args: Any) -> connection: ...
    def __exit__(self, *args: Any) -> None: ...
    def close(self) -> None: ...
    def cursor(self) -> _cursor: ...
