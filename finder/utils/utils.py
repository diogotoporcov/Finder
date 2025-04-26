import hashlib
import inspect
import io
import re
from functools import wraps
from os import PathLike
from pathlib import Path
from typing import Union, Iterable, List, TypeAlias, FrozenSet, ParamSpec, TypeVar, Callable

from PIL import Image

FilePath: TypeAlias = Union[str, Path, PathLike]
image_extensions: FrozenSet[str] = frozenset(["png", "jpg", "jpeg"])


def list_files(directory: FilePath, extensions: Iterable[str] | str) -> List[Path]:
    directory = Path(directory)

    if isinstance(extensions, str):
        extensions = [extensions]

    normalized_extensions = tuple(
        ext if ext.startswith('.') else f".{ext}" for ext in extensions
    )
    return [
        file for file in directory.iterdir()
        if file.is_file() and file.suffix in normalized_extensions
    ]


def bytes_to_hash(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def extract_name_extension(url: str, base_url: str) -> str | None:
    base_url_escaped = re.escape(base_url.rstrip("/"))
    pattern = rf"^{base_url_escaped}/image/([^/]+\.[a-zA-Z0-9]+)$"
    match = re.match(pattern, url)
    return match.group(1) if match else None


def image_to_bytesio(image: Image.Image, file_format: str = "JPEG") -> io.BytesIO:
    byte_io = io.BytesIO()
    image.save(byte_io, format=file_format)
    byte_io.seek(0)  # Move to the beginning of the BytesIO buffer
    return byte_io


_P = ParamSpec("_P")  # Represents the parameters of the function
_R = TypeVar("_R")    # Represents the return type of the function


def log_around(before: str, after: str) -> Callable[[Callable[..., _R]], Callable[..., _R]]:
    def decorator(func: Callable[..., _R]) -> Callable[..., _R]:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                print(before)
                result = await func(*args, **kwargs)
                print(after)
                return result
            return async_wrapper  # type: ignore

        @wraps(func)
        def sync_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            print(before)
            result = func(*args, **kwargs)
            print(after)
            return result
        return sync_wrapper
    return decorator
