"""Minimal Black-Scholes with no scipy dependency.

Used to translate an underlying-price path into an option P&L path, so a
signal backtested on the STOCK in TradingView can be evaluated as the
OPTION trade actually taken.
"""
import math

SQRT2 = math.sqrt(2.0)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / SQRT2))


def bs_price(S: float, K: float, T: float, r: float, sig: float, call: bool = True) -> float:
    """European option price. T in years."""
    if T <= 1e-9 or sig <= 1e-9:
        intrinsic = (S - K) if call else (K - S)
        return max(intrinsic, 0.0)
    v = sig * math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sig * sig) * T) / v
    d2 = d1 - v
    if call:
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)


def bs_delta(S: float, K: float, T: float, r: float, sig: float, call: bool = True) -> float:
    if T <= 1e-9 or sig <= 1e-9:
        itm = (S > K) if call else (S < K)
        return (1.0 if call else -1.0) if itm else 0.0
    v = sig * math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sig * sig) * T) / v
    return norm_cdf(d1) if call else norm_cdf(d1) - 1.0


def strike_for_delta(S: float, T: float, r: float, sig: float, target_delta: float,
                     call: bool = True) -> float:
    """Bisection solve for the strike whose delta matches target_delta.

    target_delta is given as a positive number for both calls and puts.
    """
    lo, hi = S * 0.30, S * 3.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        d = abs(bs_delta(S, mid, T, r, sig, call))
        # delta falls as strike rises for calls, rises as strike rises for puts
        if (d > target_delta) == call:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
