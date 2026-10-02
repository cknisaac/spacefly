"""The project's signed integer-microsecond time contract."""

INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1


def require_time_us(value: int, name: str = "time_us") -> int:
    """Require a signed 64-bit integer microsecond timestamp or duration."""
    if type(value) is not int or not INT64_MIN <= value <= INT64_MAX:
        raise ValueError(f"{name} must be a signed 64-bit integer number of microseconds")
    return value
