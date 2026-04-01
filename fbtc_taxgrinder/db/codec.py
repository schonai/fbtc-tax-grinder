"""JSON codec for serializing/deserializing dataclasses with Decimal and date."""

from __future__ import annotations

import dataclasses
import json
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, get_args, get_origin, get_type_hints


def encode(obj: object) -> str:
    """Serialize a dataclass, list, or dict to a JSON string."""
    return json.dumps(_prepare(obj), indent=2)


def decode(cls: type, text: str) -> Any:
    """Deserialize a JSON string into the given type."""
    return _reconstruct(cls, json.loads(text))


def _prepare(obj: object) -> object:
    """Convert Python objects to JSON-compatible types."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _prepare(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Decimal):
        return format(obj, "f")
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {_prepare(k): _prepare(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_prepare(v) for v in obj]
    return obj


def _reconstruct(cls: type, data: Any) -> Any:
    """Reconstruct a typed Python object from parsed JSON."""
    if data is None:
        return None
    if cls is Decimal:
        return Decimal(data)
    if cls is date:
        return date.fromisoformat(data)
    if cls is str:
        return data
    if cls is int:
        return data
    if isinstance(cls, type) and issubclass(cls, Enum):
        return cls(data)

    origin = get_origin(cls)
    args = get_args(cls)

    if origin is list:
        return [_reconstruct(args[0], item) for item in data]

    if origin is dict:
        key_type, val_type = args
        return {
            _reconstruct(key_type, k): _reconstruct(val_type, v)
            for k, v in data.items()
        }

    if dataclasses.is_dataclass(cls):
        hints = get_type_hints(cls)
        kwargs = {}
        for field_name, field_type in hints.items():
            if field_name in data:
                kwargs[field_name] = _reconstruct(field_type, data[field_name])
        return cls(**kwargs)

    return data
