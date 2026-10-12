"""JSON bridge I/O independent of the process locale, with text-stream embedding."""

import json
from typing import Any


def load_json(stream: Any) -> Any:
    """Read wire bytes directly; json retains its existing encoding detection."""
    return json.load(getattr(stream, "buffer", stream))


def write_text(stream: Any, text: str) -> None:
    """Emit UTF-8 bytes, escaping invalid code units; preserve embedded text streams."""
    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        stream.write(text)
    else:
        buffer.write(text.encode("utf-8", errors="backslashreplace"))
