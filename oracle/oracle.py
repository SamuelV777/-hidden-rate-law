"""
RB-7 Reaction Bench -- instrument driver.

An isothermal, constant-volume batch reactor charged with a single decaying species A.
Load the reactor at an initial concentration and the bench reports the half-life: the
elapsed time, in seconds, for [A] to fall from its initial value to one half of it.

Public surfaces:

    evaluate(c0)   one loading + readout.  Costs 1 unit of the run budget.
    help()         instrument notes.       Free.

The bench firmware is calibrated at the factory; its trim table is not user-serviceable.

Stdlib only. No network, no configuration, no external files.
"""

import base64
import json
import math
import random

BUDGET = 6
_spent = 0


def _build():
    """Construct the instrument surfaces over a private calibration state.

    The trim table is unpacked inside this factory and captured by the closures it
    returns. Nothing in the module namespace holds it afterwards.
    """
    raw = base64.b64decode(
        "KWBOFRovW0tFCEJDTE1EDkRAWFgMRE9WVDh+YEFYAk5ZAF9dVl9WCR0CTkNZXRBaUU5OFjRgFwMMVhsBUFddQ0ZXRBlGQxQ=")
    key = b"RB-7 thermostat trim table"
    trim = json.loads(bytes(b ^ key[i % len(key)] for i, b in enumerate(raw)).decode())

    coeffs = trim["c"]                    # rate-law coefficients, ascending order in [A]
    lo, hi, sigfigs = trim["lo"], trim["hi"], trim["sf"]
    rng = random.Random(trim["sd"])

    def rate(c):
        """Instantaneous consumption rate of A at concentration c."""
        r = 0.0
        for i, k in enumerate(coeffs):
            r += k * (c ** i)
        return r

    def integrate(a, b):
        """Adaptive Simpson on 1/rate over [a, b]; the integrand is smooth and positive."""
        f = lambda c: 1.0 / rate(c)

        def simp(x, y):
            mid = 0.5 * (x + y)
            return (y - x) / 6.0 * (f(x) + 4.0 * f(mid) + f(y))

        def rec(x, y, whole, eps, depth):
            mid = 0.5 * (x + y)
            left, right = simp(x, mid), simp(mid, y)
            if depth > 80 or abs(left + right - whole) <= 15.0 * eps:
                return left + right + (left + right - whole) / 15.0
            return (rec(x, mid, left, eps / 2.0, depth + 1)
                    + rec(mid, y, right, eps / 2.0, depth + 1))

        whole = simp(a, b)
        return rec(a, b, whole, 1e-15 * max(1.0, abs(whole)), 0)

    def half_life(c0):
        return integrate(0.5 * c0, c0)

    def round_sig(x, n):
        if x == 0.0:
            return 0.0
        return round(x, -int(math.floor(math.log10(abs(x)))) + (n - 1))

    def charge(n=1):
        global _spent
        if _spent + n > BUDGET:
            raise RuntimeError(
                "run budget exhausted: %d/%d units already spent" % (_spent, BUDGET))
        _spent += n

    def evaluate(c0):
        """Charge the reactor to c0 mol/L and report the half-life of A, in seconds.

        Costs 1 unit of the run budget. Readings are exact and reproducible, quoted to
        the bench's rated precision.
        """
        c0 = float(c0)
        if c0 != c0 or c0 in (float("inf"), float("-inf")):
            raise ValueError("c0 must be a finite concentration in mol/L")
        if c0 < lo or c0 > hi:
            raise ValueError(
                "c0 = %g mol/L is outside the bench's charging range [%g, %g] mol/L"
                % (c0, lo, hi))
        charge()
        return round_sig(half_life(c0), sigfigs)

    def help():
        """Instrument notes. Free -- does not touch the run budget."""
        return (
            "RB-7 Reaction Bench\n"
            "-------------------\n"
            "Single species A decaying in an isothermal, constant-volume batch reactor.\n"
            "The consumption rate of A is a fixed function of the current concentration of\n"
            "A and of nothing else: no temperature programme, no second reagent, no\n"
            "induction period, no back reaction.\n"
            "\n"
            "evaluate(c0) charges the reactor to c0 mol/L and returns the half-life of A in\n"
            "seconds -- the time for [A] to fall from c0 to c0/2.\n"
            "\n"
            "  charging range : %g to %g mol/L\n"
            "  rated precision: %d significant figures\n"
            "  run budget     : %d loadings\n"
            "\n"
            "Readings are exact and reproducible: the same c0 always returns the same\n"
            "number, and repeating a loading you have already made spends a unit to learn\n"
            "nothing.\n"
            "\n"
            "Operator's note. The charging range spans twelve decades. That is not\n"
            "generosity; it is the working range over which this bench was characterised.\n"
            "Readings clustered inside a single decade constrain the chemistry far less\n"
            "than their tidiness suggests, and a bench run planned around convenient\n"
            "concentrations will produce a clean, self-consistent fit to a reactor that\n"
            "does not exist.\n"
            % (lo, hi, sigfigs, BUDGET)
        )

    def sample():
        """Uncalibrated spot reading from the bench's idle-loop monitor.

        Draws its own charge concentration and reports through the unregulated preamp.
        Costs 1 unit of the run budget.
        """
        charge()
        c0 = 10.0 ** rng.uniform(math.log10(lo), math.log10(hi))
        t = half_life(c0) * math.exp(rng.gauss(0.0, 0.04))
        return {
            "c0": round_sig(c0, sigfigs),
            "t_half": round_sig(t, sigfigs),
            "channel": "idle-loop monitor (uncalibrated)",
        }

    return evaluate, help, sample


evaluate, help, sample = _build()

# The factory has run; drop it so the trim table cannot be unpacked a second time from
# the module namespace.
del _build
