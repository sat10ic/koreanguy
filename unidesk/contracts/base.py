"""Shared validation + serialization helpers for unidesk contracts.

Style and rules adopted from `orderflow/market_data/schemas.py` (one-way
dependency per unidesk DECISIONS.md D4). Non-negotiables (build manual P0.2
acceptance + R12): unknown enum values fail closed; nulls stay null and are
never substituted with invented fallbacks; time-sensitive snapshots carry a
mandatory timezone-aware `as_of`; version/hash fields are mandatory where the
manual specifies them; serialization is stable for identical input.
"""
from __future__ import annotations

import dataclasses
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional, Type, TypeVar

T = TypeVar("T")


class ContractError(ValueError):
    """A contract was constructed from impossible or incomplete data."""


def ensure_utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise ContractError(f"{field} must be a datetime, got {value!r}")
    if value.tzinfo is None:
        raise ContractError(f"{field} must be timezone-aware, got naive {value!r}")
    return value.astimezone(timezone.utc)


def ensure_date(value: date, field: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ContractError(f"{field} must be a date, got {value!r}")
    return value


def require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string, got {value!r}")
    return value


def require_opt_str(value: Optional[str], field: str) -> Optional[str]:
    if value is None:
        return None
    return require_str(value, field)


def require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{field} must be a bool, got {value!r}")
    return value


def require_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{field} must be an int, got {value!r}")
    return value


def require_opt_int(value: Any, field: str) -> Optional[int]:
    if value is None:
        return None
    return require_int(value, field)


def require_float(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{field} must be a number, got {value!r}")
    out = float(value)
    if out != out or out in (float("inf"), float("-inf")):
        raise ContractError(f"{field} must be finite, got {value!r}")
    return out


def require_opt_float(value: Any, field: str) -> Optional[float]:
    if value is None:
        return None
    return require_float(value, field)


def require_non_negative(value: float, field: str) -> float:
    if value < 0:
        raise ContractError(f"{field} must be non-negative, got {value}")
    return value


def require_unit_interval(value: Optional[float], field: str) -> Optional[float]:
    """Confidence-style fields: 0..1 or null. Null is never coerced to 0."""
    if value is None:
        return None
    out = require_float(value, field)
    if not 0.0 <= out <= 1.0:
        raise ContractError(f"{field} must be within 0..1, got {out}")
    return out


def coerce_enum(value: Any, enum_type: Type[Enum], field: str) -> Enum:
    """Coerce ``value`` (member or raw string) to ``enum_type``; unknown
    values fail closed. Signature is (value, type, field) — the order every
    contract call site uses."""
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except ValueError:
        # Fail closed on unknown values (P0.2 acceptance: unknown enum values fail)
        raise ContractError(
            f"{field}={value!r} is not a valid {enum_type.__name__}: "
            f"known values are {[e.value for e in enum_type]}"
        )


def require_str_tuple(value: Any, field: str) -> tuple:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ContractError(f"{field} must be a list of strings, got {value!r}")
    return tuple(require_str(v, f"{field}[]") for v in value)


def to_dict(obj: Any) -> Any:
    """Stable serialization: dataclasses -> dicts, enums -> values,
    datetimes/dates -> ISO strings, tuples -> lists. Identical input always
    produces identical output (P0.2 acceptance)."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_dict(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, (list, tuple)):
        return [to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): to_dict(v) for k, v in obj.items()}
    return obj


def from_dict(cls: Type[T], data: Any) -> T:
    """Reconstruct a dataclass contract from its `to_dict()` output.

    Nested dataclasses (including inside lists/tuples) are reconstructed by
    field type; unknown keys are rejected so schema drift fails loudly.
    """
    if not isinstance(data, dict):
        raise ContractError(f"{cls.__name__} expects a dict, got {type(data)!r}")
    if not is_dataclass(cls):
        raise ContractError(f"from_dict target {cls} is not a dataclass")
    field_names = {f.name for f in fields(cls)}
    unknown = set(data) - field_names
    if unknown:
        raise ContractError(f"{cls.__name__} got unknown keys: {sorted(unknown)}")
    try:
        import typing
        hints = typing.get_type_hints(cls)
    except Exception:
        hints = {}
    kwargs: dict[str, Any] = {}
    for f in fields(cls):
        if f.name not in data:
            raise ContractError(f"{cls.__name__} missing key: {f.name}")
        resolved = hints.get(f.name, f.type)
        kwargs[f.name] = _revive(resolved if isinstance(resolved, type) or typing.get_origin(resolved) is not None else None, data[f.name])
    return cls(**kwargs)


def _revive(field_type: Any, value: Any) -> Any:
    if value is None:
        return None
    # ISO strings revive into datetimes/dates for datetime-typed fields
    if isinstance(value, str):
        target = _plain_type(field_type)
        if target is datetime:
            return datetime.fromisoformat(value)
        if target is date:
            return date.fromisoformat(value)
        return value
    if isinstance(value, list):
        inner = _unwrap_optional_or_container(field_type)
        if inner is not None and is_dataclass(inner) and not isinstance(inner, type):
            return tuple(from_dict(inner, v) for v in value)
        return value
    if isinstance(value, dict):
        inner = _unwrap_optional_or_container(field_type)
        if inner is not None and is_dataclass(inner) and not isinstance(inner, type):
            return from_dict(inner, value)
        return value
    return value


def _plain_type(field_type: Any) -> Optional[type]:
    """The bare class behind Optional[X] / X, else None."""
    import typing
    import inspect

    if inspect.isclass(field_type):
        return field_type
    if typing.get_origin(field_type) is typing.Union:
        for arg in typing.get_args(field_type):
            if inspect.isclass(arg) and arg is not type(None):
                return arg
    return None


def _unwrap_optional_or_container(field_type: Any) -> Optional[type]:
    """Best-effort: resolve the dataclass hidden behind typing constructs.
    Falls back to None for non-generic annotations (string forward refs on
    Python <3.10 style); those contracts are reconstructed as plain values."""
    import typing
    import inspect

    if not isinstance(field_type, type) and typing.get_origin(field_type) is None:
        return None
    if typing.get_origin(field_type) in (list, tuple):
        args = typing.get_args(field_type)
        if args and is_dataclass(args[0]):
            return args[0]
        return None
    if typing.get_origin(field_type) is typing.Union:
        for arg in typing.get_args(field_type):
            if inspect.isclass(arg) and is_dataclass(arg):
                return arg
        return None
    if inspect.isclass(field_type) and is_dataclass(field_type):
        return field_type
    return None
