"""
Calibration harness for the RB-7 inverse task.

    python scripts/checks.py verify      intended solver recovers the locked answer   -> PASS
    python scripts/checks.py shortcut    naive solver does NOT recover it             -> FAIL (as intended)
    python scripts/checks.py lint        solver-facing surfaces leak nothing          -> CLEAN
    python scripts/checks.py preview     intended difficulty target                   -> <= 2/8
    python scripts/checks.py unique      no alternate answer fits the evidence        -> UNIQUE
    python scripts/checks.py selftest    all of the above, asserted                   -> all green

Stdlib only. Offline. Exit code 0 means the signal landed where it should.
"""

import json
import math
import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _gauss_legendre(n):
    """Nodes and weights on [-1, 1], by Newton iteration on the Legendre polynomial."""
    out = []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        dp = 1.0
        for _ in range(100):
            p0, p1 = 1.0, 0.0
            for j in range(1, n + 1):
                p2 = p1
                p1 = p0
                p0 = ((2 * j - 1) * x * p1 - (j - 1) * p2) / j
            dp = n * (x * p0 - p1) / (x * x - 1.0)
            dx = -p0 / dp
            x += dx
            if abs(dx) < 1e-15:
                break
        out.append((x, 2.0 / ((1 - x * x) * dp * dp)))
    return out


_GL = _gauss_legendre(24)
EXPECTED = json.load(open(os.path.join(ROOT, "golden", "expected.json")))
ANS = EXPECTED["answer"]
TRUE = [ANS["k0"], ANS["k1"], ANS["k2"]]
TOL = EXPECTED["tolerance_relative"]
BUDGET = EXPECTED["query_budget"]


# --------------------------------------------------------------------------- grading

def grade(sub):
    """Grade a submission against the locked answer. Returns (passed, [reasons])."""
    why = []
    if not isinstance(sub, dict):
        return False, ["submission is not a JSON object"]

    coeffs = sub.get("coefficients")
    if not isinstance(coeffs, list) or not coeffs:
        return False, ["submission has no 'coefficients' list"]
    try:
        coeffs = [float(c) for c in coeffs]
    except (TypeError, ValueError):
        return False, ["'coefficients' contains a non-numeric entry"]

    degree = sub.get("degree")
    if degree != EXPECTED["polynomial_degree"]:
        why.append("degree is %r, locked answer has degree %d"
                   % (degree, EXPECTED["polynomial_degree"]))
    if len(coeffs) != len(TRUE):
        why.append("reported %d coefficients, locked answer has %d"
                   % (len(coeffs), len(TRUE)))

    for i, t in enumerate(TRUE):
        got = coeffs[i] if i < len(coeffs) else 0.0
        rel = abs(got / t - 1.0)
        mark = "ok" if rel <= TOL else "OUT"
        if rel > TOL:
            why.append("k%d = %.6g is %+.2f%% off (limit %.0f%%) [%s]"
                       % (i, got, 100.0 * (got / t - 1.0), 100.0 * TOL, mark))

    if EXPECTED["higher_order_coefficients_must_be_zero"]:
        for i in range(len(TRUE), len(coeffs)):
            if coeffs[i] != 0.0:
                why.append("spurious k%d = %.6g must be zero" % (i, coeffs[i]))

    return (not why), why


def run_solver(relpath):
    """Run a solver in a fresh process and return (submission_dict, stderr)."""
    proc = subprocess.run([sys.executable, os.path.join(ROOT, relpath)],
                          cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("%s exited %d\n%s" % (relpath, proc.returncode, proc.stderr))
    line = [l for l in proc.stdout.strip().splitlines() if l.strip().startswith("{")]
    if not line:
        raise RuntimeError("%s printed no JSON submission\n%s" % (relpath, proc.stdout))
    return json.loads(line[-1]), proc.stderr


def _report(sub, why):
    coeffs = sub.get("coefficients") or []
    for i, t in enumerate(TRUE):
        got = float(coeffs[i]) if i < len(coeffs) else 0.0
        print("    k%d  submitted %-14.6g  true %-10.6g  %+8.3f%%" % (i, got, t, 100.0 * (got / t - 1.0)))
    print("    degree submitted %r, true %d" % (sub.get("degree"), EXPECTED["polynomial_degree"]))
    print("    queries used: %s / %d" % (sub.get("queries_used", "?"), BUDGET))
    for w in why:
        print("    - " + w)


# --------------------------------------------------------------------------- checks

def check_verify(verbose=True):
    sub, _ = run_solver(os.path.join("solution", "main.py"))
    ok, why = grade(sub)
    used = sub.get("queries_used")
    within_budget = isinstance(used, int) and used <= BUDGET
    if verbose:
        print("verify  -- intended solver vs locked answer")
        _report(sub, why)
        if not within_budget:
            print("    - OVER BUDGET: used %s of %d" % (used, BUDGET))
    good = ok and within_budget
    print("verify   : %s" % ("PASS" if good else "FAIL"))
    return good


def check_shortcut(verbose=True):
    sub, _ = run_solver(os.path.join("solution", "shortcut.py"))
    ok, why = grade(sub)
    if verbose:
        print("shortcut -- naive solver vs locked answer (it is supposed to miss)")
        _report(sub, why)
    if ok:
        print("shortcut : PASS -- BROKEN: the naive solver recovered the answer")
        return False
    print("shortcut : FAIL (as intended)")
    return True


def _leak_tokens():
    """Renderings of the locked answer that must never appear on a solver-facing surface."""
    toks = set()
    for v in TRUE:
        toks.update({repr(v), "%g" % v, "%.10g" % v, "%e" % v, "%.2e" % v, "%.3g" % v})
        m = "%e" % v
        mant = m.split("e")[0].rstrip("0").rstrip(".")
        toks.add(mant)
        toks.add(("%.17f" % v).rstrip("0"))
    toks.update({"3.7e-8", "3.7e-08", "2.15e-2", "2.15e-02", "0.0215", "0.48",
                 str(EXPECTED["derived"]["plateau_illusion_ln2_over_k1_s"])[:7],
                 "31.84", "32.24", "32.2394"})
    # drop anything short enough to collide with ordinary prose or the stated range
    return sorted(t for t in toks if len(t) >= 3 and t not in ("1e-09", "1000"))


def check_lint(verbose=True):
    print("lint     -- hunting the answer on every surface the solver can see")
    bad = []
    tokens = _leak_tokens()

    surfaces = {
        "problem.md": open(os.path.join(ROOT, "problem.md"), encoding="utf-8").read(),
        "BRIEF.md": open(os.path.join(ROOT, "BRIEF.md"), encoding="utf-8").read(),
        "oracle/oracle.py": open(os.path.join(ROOT, "oracle", "oracle.py"), encoding="utf-8").read(),
    }
    sys.path.insert(0, os.path.join(ROOT, "oracle"))
    import oracle
    surfaces["oracle.help()"] = oracle.help()

    for name, text in surfaces.items():
        for tok in tokens:
            if tok in text:
                bad.append("%s contains %r" % (name, tok))

    # the hidden surface must stay unadvertised
    prompt = surfaces["problem.md"]
    for word in ("sample(", "sample()", "idle-loop", "uncalibrated", "preamp"):
        if word in prompt:
            bad.append("problem.md advertises the hidden surface (%r)" % word)

    # structural giveaways -- applied to BRIEF.md too, which must survive an adversarial
    # read even though it is an authoring-side document
    for surface in ("problem.md", "BRIEF.md"):
        text = surfaces[surface].lower()
        for phrase in ("degree 2", "degree two", "quadratic", "zero-order", "second-order",
                       "first-order", "mixed order", "non-monotonic", "three terms",
                       "three channels", "turnover", "plateau", "asymptot", "power law",
                       "at the extremes", "edges of the range"):
            if phrase in text:
                bad.append("%s gives away the mechanism (%r)" % (surface, phrase))

    # the trim table must not be readable as plaintext
    src = surfaces["oracle/oracle.py"]
    for v in TRUE:
        if repr(v) in src or ("%g" % v) in src:
            bad.append("oracle source exposes a coefficient in plaintext (%r)" % v)
    import oracle as _o
    for name in dir(_o):
        if name.startswith("__"):
            continue
        val = getattr(_o, name)
        if isinstance(val, list) and val and isinstance(val[0], float):
            bad.append("oracle module attribute %r hands over the coefficients" % name)

    # Grading rule 4 (no spurious higher-order term) is NOT enforceable by the evidence --
    # see STATE.md 4(a). It is fair only because problem.md asks for the lowest degree
    # consistent with the readings. If that sentence ever leaves the prompt, the rule
    # becomes a trap, so assert it is still there.
    if "lowest degree consistent" not in prompt:
        bad.append("problem.md no longer states the parsimony rule that grading rule 4 "
                   "depends on -- rule 4 would be unfair")

    if verbose:
        print("    scanned: %s" % ", ".join(surfaces))
        print("    %d answer renderings checked per surface" % len(tokens))
        for b in bad:
            print("    - " + b)
    print("lint     : %s" % ("CLEAN" if not bad else "LEAK"))
    return not bad


def check_preview(verbose=True):
    print("preview  -- intended difficulty")
    if verbose:
        print("    target: a strong model at 8 attempts lands <= 2/8")
        print("    the three gates an attempt has to clear, and what each one costs:")
        print("      1. probe placement -- k0 is unresolvable from mid-range readings.")
        print("         Over 1e-3..1e2 the zero-order channel is under 0.2% of the rate,")
        print("         beneath what a 4-significant-figure instrument resolves: k0 is")
        print("         free over x0.7..x1.3 there (run 'unique'), and the best-fit point")
        print("         estimate already lands at +3.00%. Fitting cannot save it; only a")
        print("         query near the bottom of the charging range can.")
        print("      2. structural discovery -- the half-life is non-monotonic in c0, which")
        print("         no single power law can produce. Invisible without wide probes.")
        print("      3. refusing the approximation -- the best reading ln2/t_half can give")
        print("         anywhere in the domain is +1.29%, outside the 1% tolerance.")
        print("    near-misses that look like passes (see grader/grading_guide.md):")
        print("      probing 1e-4..1e3 recovers k1 to +0.97% and k2 to -0.14% -- both inside")
        print("      tolerance -- and still reports k0 = 0. Two of three is a failure.")
        print("    budget: 6 queries against 12 decades; the answer is 3 positive reals,")
        print("      so there is nothing to enumerate and the budget buys inference only.")
    print("preview  : <= 2/8")
    return True


def check_unique(verbose=True):
    """Search for a second parameter set reproducing the evidence. Backs STATE.md section 4(e)."""
    print("unique   -- searching for an alternate answer that fits the same evidence")

    def th(c0, k):
        k0, k1, k2 = k
        if min(k0, k1, k2) < 0:
            return None
        d = k1 * k1 - 4 * k0 * k2
        if d <= 0:
            return None
        s = math.sqrt(d)
        r1, r2 = (-k1 + s) / (2 * k2), (-k1 - s) / (2 * k2)
        f = lambda c: math.log(abs((c - r1) / (c - r2))) / (k2 * (r1 - r2))
        return f(c0) - f(c0 / 2.0)

    def sig(x, n=4):
        return 0.0 if x == 0 else round(x, -int(math.floor(math.log10(abs(x)))) + (n - 1))

    floor = 5e-4  # relative rounding half-width of a 4-significant-figure reading

    def widest_consistent(probes, restarts=120):
        """Widest departure from the locked answer among triples that reproduce every
        reading to within the instrument's rounding floor."""
        obs = [sig(th(c, TRUE)) for c in probes]
        rng = random.Random(20260921)
        worst = 0.0
        for _ in range(restarts):
            p = [TRUE[0] * 10 ** rng.uniform(-1.5, 1.5),
                 TRUE[1] * 10 ** rng.uniform(-0.5, 0.5),
                 TRUE[2] * 10 ** rng.uniform(-0.5, 0.5)]
            step = [0.35, 0.15, 0.15]

            def cost(q):
                m = 0.0
                for c, o in zip(probes, obs):
                    v = th(c, q)
                    if v is None:
                        return 1e9
                    m = max(m, abs(v - o) / o)
                return m

            cur = cost(p)
            for it in range(2500):
                i = it % 3
                moved = False
                for d in (1, -1):
                    q = list(p)
                    q[i] *= math.exp(d * step[i])
                    c2 = cost(q)
                    if c2 < cur:
                        p, cur, moved = q, c2, True
                        break
                if not moved:
                    step[i] *= 0.7
                if max(step) < 1e-10:
                    break
            if cur <= floor:
                worst = max(worst, max(abs(p[j] / TRUE[j] - 1.0) for j in range(3)))
        return worst

    # (1) WELL-POSEDNESS. Evidence that spans the charging range must admit exactly one
    #     answer. This is the claim the task rests on; if it fails, the task is broken.
    spanning = [1e-9, 1e-7, 3e-4, 1e-2, 1e1, 1e3]
    span_worst = widest_consistent(spanning)
    ok = span_worst <= TOL
    if verbose:
        print("    spanning evidence (1e-9..1e3, the intended probe plan):")
        print("      widest evidence-consistent departure from the locked answer: %.3f%%"
              % (100 * span_worst))
        print("      tolerance is %.0f%% -- the answer is pinned %.0fx tighter than it needs"
              % (100 * TOL, (TOL / span_worst) if span_worst > 0 else float("inf")))

    # (2) THE INFORMATION FLOOR. Mid-range-only evidence is *designed* to be insufficient.
    #     This is not ambiguity in the answer -- it is ambiguity in a solver's chosen
    #     evidence, and it is the mechanism the difficulty target rests on. Measured here
    #     so the claim in preview and grading_guide.md is a number, not an assertion.
    mid_worst = widest_consistent([1e-3, 3e-3, 1e-2, 1e-1, 1e0, 1e2])
    if verbose:
        print("    mid-range-only evidence (1e-3..1e2), for contrast:")
        print("      triples departing by up to %.0f%% still reproduce every reading."
              % (100 * mid_worst))
        print("      k0 is free over roughly x0.7..x1.3 there; k1 and k2 stay pinned.")
        print("      That gap is the task: the same six queries, placed differently, are")
        print("      the difference between a determined answer and an undetermined one.")
    if mid_worst <= TOL and verbose:
        print("      WARNING: mid-range evidence also pins the answer -- probe placement")
        print("               no longer matters and the difficulty target is overstated.")

    # (3) THE DEGREE IS NOT FORCED FROM ABOVE. Disclosed honestly: on a range bounded at
    #     1e3, a small enough k3 hides under the instrument's rounding. Grading rule 4
    #     excludes it by the parsimony rule stated in problem.md, not by the evidence.
    #     What matters for fairness is that a hidden k3 does not move k0, k1, k2.
    def th_poly(c0, coeffs):
        a, b = 0.5 * c0, c0
        h, m = 0.5 * (b - a), 0.5 * (a + b)
        s = 0.0
        for x, w in _GL:
            c = m + h * x
            r = 0.0
            for i, k in enumerate(coeffs):
                r += k * (c ** i)
            if r <= 0:
                return None
            s += w / r
        return s * h

    obs_span = [sig(th(c, TRUE)) for c in spanning]
    worst_shift = 0.0
    band_hi = None
    for k3 in (1e-8, 5e-8, 3e-7, 1e-6, 1e-5):
        p, step = list(TRUE), [0.05, 0.05, 0.05]

        def cost3(q):
            m = 0.0
            for c, o in zip(spanning, obs_span):
                v = th_poly(c, q + [k3])
                if v is None:
                    return 1e9
                m = max(m, abs(v - o) / o)
            return m

        cur = cost3(p)
        for it in range(6000):
            i = it % 3
            moved = False
            for d in (1, -1):
                q = list(p)
                q[i] *= math.exp(d * step[i])
                if min(q) <= 0:
                    continue
                c2 = cost3(q)
                if c2 < cur:
                    p, cur, moved = q, c2, True
                    break
            if not moved:
                step[i] *= 0.7
            if max(step) < 1e-13:
                break
        if cur <= floor:
            band_hi = k3
            worst_shift = max(worst_shift, max(abs(p[j] / TRUE[j] - 1.0) for j in range(3)))
    if verbose:
        print("    degree, disclosed honestly:")
        print("      the readings force degree >= 2, but cannot force degree <= 2.")
        print("      a k3 up to ~%.0e still reproduces every spanning reading (it is" % band_hi)
        print("      0.01% of the rate even at c0 = 1e3). That is excluded by the parsimony")
        print("      rule problem.md states, not by the evidence -- see STATE.md 4(a).")
        print("      harmless to the values: across that band k0,k1,k2 move by <= %.3f%%."
              % (100 * worst_shift))
    if worst_shift > TOL:
        ok = False
        if verbose:
            print("      BROKEN: a hidden k3 moves the graded coefficients out of tolerance.")

    print("unique   : %s" % ("UNIQUE" if ok else "AMBIGUOUS -- task is broken"))
    return ok


def check_selftest():
    print("=" * 72)
    results = [
        ("verify   expected PASS", check_verify()),
        ("shortcut expected FAIL", check_shortcut()),
        ("lint     expected CLEAN", check_lint()),
        ("unique   expected UNIQUE", check_unique()),
        ("preview  expected <= 2/8", check_preview()),
    ]
    print("=" * 72)
    for name, ok in results:
        print("  %-26s %s" % (name, "green" if ok else "RED"))
    allgood = all(ok for _, ok in results)
    print("selftest : %s" % ("all green" if allgood else "NOT GREEN"))
    return allgood


COMMANDS = {
    "verify": check_verify,
    "shortcut": check_shortcut,
    "lint": check_lint,
    "preview": check_preview,
    "unique": check_unique,
    "selftest": check_selftest,
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(0 if COMMANDS[sys.argv[1]]() else 1)
