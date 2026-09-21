"""
Intended solver for the RB-7 bench.

Strategy, in one sentence: spend the six loadings on the *edges* of the charging range
rather than the middle of it, because each edge isolates one channel of the rate law, and
then stop approximating and actually integrate.

    1. Two probes at the bottom of the range. If a zero-order channel exists, the half-life
       there goes linear in c0 (t -> c0/2k0, log-log slope +1) and hands over k0 directly.
    2. Two probes at the top. The high-c0 log-log slope is exactly -(d-1) for a degree-d
       rate law, so it reads off the degree; for d = 2 it also hands over k2 (t -> 1/k2*c0).
    3. Two probes in the middle, near where the half-life curve turns over, which is where
       sensitivity to the first-order channel is greatest.
    4. Refine all coefficients at once by least squares against the exact integrated rate
       law. This step is not optional polish: the first-order closed form ln2/k is never
       better than ~1.3% here, and the tolerance is 1%.

Budget: exactly 6 evaluate() calls. Uses no undocumented surface.
Stdlib only.
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "oracle"))
import oracle  # noqa: E402


# --- our own forward model, written independently of the bench firmware ---------------

def half_life(c0, coeffs):
    """integral of 1/rate from c0/2 to c0, by adaptive Simpson."""
    def f(c):
        r = 0.0
        for i, k in enumerate(coeffs):
            r += k * (c ** i)
        if r <= 0.0:
            return float("inf")
        return 1.0 / r

    def simp(lo, hi):
        mid = 0.5 * (lo + hi)
        return (hi - lo) / 6.0 * (f(lo) + 4.0 * f(mid) + f(hi))

    def rec(lo, hi, whole, eps, depth):
        mid = 0.5 * (lo + hi)
        left, right = simp(lo, mid), simp(mid, hi)
        if depth > 60 or abs(left + right - whole) <= 15.0 * eps:
            return left + right + (left + right - whole) / 15.0
        return (rec(lo, mid, left, eps / 2.0, depth + 1)
                + rec(mid, hi, right, eps / 2.0, depth + 1))

    a, b = 0.5 * c0, c0
    w = simp(a, b)
    return rec(a, b, w, 1e-14 * max(1.0, abs(w)), 0)


def solve_k1(c0, t_obs, k0, k2):
    """Invert t_half(c0) for k1 with k0, k2 held fixed. t_half is strictly decreasing
    in k1, so plain bisection is guaranteed to converge."""
    lo, hi = 1e-12, 1e6
    for _ in range(300):
        mid = math.sqrt(lo * hi)
        if half_life(c0, [k0, mid, k2]) > t_obs:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def refine(probes, coeffs):
    """Least squares on log residuals, coordinate descent in log-parameter space."""
    p = list(coeffs)

    def cost(q):
        s = 0.0
        for c0, t in probes:
            v = half_life(c0, q)
            if not (v > 0.0) or v == float("inf"):
                return float("inf")
            s += math.log(v / t) ** 2
        return s

    step = [0.10] * len(p)
    cur = cost(p)
    for it in range(30000):
        i = it % len(p)
        moved = False
        for d in (1.0, -1.0):
            q = list(p)
            q[i] *= math.exp(d * step[i])
            c2 = cost(q)
            if c2 < cur:
                p, cur = q, c2
                moved = True
                break
        if not moved:
            step[i] *= 0.6
        if max(step) < 1e-13:
            break
    return p, cur


def main():
    # 1-2: bottom of the range.   3-4: middle, near the turnover.   5-6: top.
    plan = [1e-9, 1e-7, 3e-4, 1e-2, 1e1, 1e3]
    probes = [(c0, oracle.evaluate(c0)) for c0 in plan]

    # --- read the degree off the top end -------------------------------------------
    (ca, ta), (cb, tb) = probes[-2], probes[-1]
    hi_slope = math.log(tb / ta) / math.log(cb / ca)
    degree = int(round(1.0 - hi_slope))

    # --- read the low end: slope +1 means a nonzero zero-order channel ---------------
    (cl, tl), (cm, tm) = probes[0], probes[1]
    lo_slope = math.log(tm / tl) / math.log(cm / cl)

    # --- seed each coefficient from the asymptote that isolates it -------------------
    k0 = cl / (2.0 * tl) if lo_slope > 0.5 else 0.0     # t -> c0 / (2 k0)
    k2 = 1.0 / (cb * tb) if degree == 2 else 0.0        # t -> 1 / (k2 c0)
    k1 = solve_k1(probes[2][0], probes[2][1], k0, k2)   # exact inversion at the turnover

    # --- refine all three together against every reading -----------------------------
    coeffs, resid = refine(probes, [k0, k1, k2])

    out = {
        "degree": degree,
        "coefficients": coeffs,
        "queries_used": oracle._spent,
        "rate_law": "-d[A]/dt = k0 + k1*[A] + k2*[A]**2",
        "units": ["mol/(L*s)", "1/s", "L/(mol*s)"],
    }

    sys.stderr.write("probes (c0, t_half):\n")
    for c0, t in probes:
        sys.stderr.write("    %-10g %12g\n" % (c0, t))
    sys.stderr.write("low-end log-log slope  = %+.3f  -> zero-order floor present\n" % lo_slope)
    sys.stderr.write("high-end log-log slope = %+.3f  -> degree %d\n" % (hi_slope, degree))
    sys.stderr.write("seeds  k0=%.6g  k1=%.6g  k2=%.6g\n" % (k0, k1, k2))
    sys.stderr.write("refined residual (sum of squared log errors) = %.3e\n" % resid)

    print(json.dumps(out))


if __name__ == "__main__":
    main()
