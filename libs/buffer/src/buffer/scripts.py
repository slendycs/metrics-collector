from functools import cache
from importlib.resources import files


@cache
def load_script(name: str) -> str:
    """Читает Lua-скрипт из пакета: load_script("put_bid")."""
    return (files("buffer") / "lua" / f"{name}.lua").read_text(encoding="utf-8")
