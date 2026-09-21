"""
The naive solver -- the method of half-lives, applied the way it is taught.

This is not a strawman. It is the standard undergraduate procedure for determining a
reaction order from half-life data, executed correctly:

    For a rate law -d[A]/dt = k[A]^n, the half-life scales as

        t_half  proportional to  c0^(1-n)

    so a log-log plot of half-life against initial concentration has slope (1 - n).
    Fit the slope, read off n, then back out k from the integrated rate law for that n.

The procedure is sound. Everything that follows from it here is wrong, and the reason is
documented in reasoning_trap.md.

Budget: 6 evaluate() calls -- the same budget the intended solver gets.
Stdlib only.
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "oracle"))
import oracle  # noqa: E402


def main():
    # A sensible bench run: millimolar to centimolar, geometrically spaced, six points
    # across a decade and a half. These are the concentrations you would actually charge
    # a reactor to, and the spacing a careful experimentalist would choose.
    plan = [5e-4, 1e-3, 2e-3, 4e-3, 8e-3, 1.6e-2]
    probes = [(c0, oracle.evaluate(c0)) for c0 in plan]

    # Least-squares slope of ln(t_half) against ln(c0).
    xs = [math.log(c0) for c0, _ in probes]
    ys = [math.log(t) for _, t in probes]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)

    order = 1.0 - slope

    # The fitted order is 1.06. Within the scatter of a real bench that is first order,
    # and a fractional order of 1.06 has no mechanistic meaning, so: round to 1.
    order_int = int(round(order))

    # First order => half-life is independent of c0 => k = ln2 / t_half.
    # Average the readings, since under this model they are all measuring the same thing.
    t_mean = sum(t for _, t in probes) / n
    k = math.log(2.0) / t_mean

    out = {
        "degree": order_int,
        "coefficients": [0.0, k],
        "queries_used": oracle._spent,
        "rate_law": "-d[A]/dt = k1*[A]   (first order)",
        "units": ["mol/(L*s)", "1/s"],
    }

    sys.stderr.write("probes (c0, t_half):\n")
    for c0, t in probes:
        sys.stderr.write("    %-10g %12g\n" % (c0, t))
    sys.stderr.write("log-log slope = %+.4f  -> apparent order n = %.3f, call it %d\n"
                     % (slope, order, order_int))
    ts = [t for _, t in probes]
    sys.stderr.write("half-lives vary by only %.1f%% across the run; treating as constant\n"
                     % (100.0 * (max(ts) - min(ts)) / max(ts)))
    sys.stderr.write("k = ln2 / mean(t_half) = %.6g 1/s\n" % k)

    print(json.dumps(out))


if __name__ == "__main__":
    main()
