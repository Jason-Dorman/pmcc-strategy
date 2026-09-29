from collections.abc import Callable

def brentq(
    f: Callable[[float], float],
    a: float,
    b: float,
    xtol: float = ...,
    rtol: float = ...,
    maxiter: int = ...,
) -> float: ...
