import math
from typing import Any

def sanitize_for_json(obj: Any) -> Any:
    """Recursively convert objects that are not JSON serializable into safe primitives.

    - numpy scalars -> native python scalars
    - NaN / inf -> None
    - bytes -> string (utf-8)
    """
    # handle simple scalars first
    try:
        import numpy as _np
    except Exception:
        _np = None

    # numpy scalars
    if _np is not None and isinstance(obj, _np.generic):
        return sanitize_for_json(obj.item())

    # bytes
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode("utf-8")
        except Exception:
            return str(obj)

    # floats: handle nan/inf
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    # ints, bool, str, None
    if isinstance(obj, (int, bool, str)) or obj is None:
        return obj

    # lists/tuples
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(x) for x in obj]

    # dicts
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}

    # fallback: try to convert to string
    try:
        return str(obj)
    except Exception:
        return None
