def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    if b == 0:
        return default
    return a / b


def to_percent(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"
