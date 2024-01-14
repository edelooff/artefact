from typing import TypeVar

T = TypeVar("T")


def tag_escape(tag: str) -> str:
    """Escapes characters that AO3 requires to be non-literal."""
    return (
        tag.replace(".", "*d*")
        .replace("#", "*h*")
        .replace("?", "*q*")
        .replace("/", "*s*")
    )


def unwrap(option: T | None) -> T:
    """Unwraps the input type from an Optional to satisfy mypy.

    Raises a RuntimeError when the input value is None.

    Inspired by Rust's unwrap function:
    https://doc.rust-lang.org/std/option/enum.Option.html#method.unwrap
    """
    if option is None:
        raise RuntimeError("Unexpected None-value")
    return option
