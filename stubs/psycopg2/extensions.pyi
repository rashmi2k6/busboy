import typing as t

class cursor:
    def __enter__(self, *args: t.Any) -> cursor: ...
    def __exit__(self, *args: t.Any) -> None: ...
    def mogrify(self, query: str, items: t.Tuple[t.Any, ...]) -> str: ...
    def execute(self, query: str) -> None: ...
    def fetchall(self) -> t.Iterable[t.Tuple[t.Any, ...]]: ...
class connection:
    def __enter__(self, *args: t.Any) -> connection: ...
    def __exit__(self, *args: t.Any) -> None: ...
    def cursor(self) -> psycopg2.extensions.cursor: ...
