# reasoning_trap.md — what the shortcut falls into, and why it is a fair trap

## The shortcut, stated plainly

`solution/shortcut.py` runs the **method of half-lives**, which is the standard procedure
for determining a reaction order and is taught in every introductory kinetics course:

> For `-d[A]/dt = k[A]^n`, the half-life scales as `t½ ∝ c0^(1-n)`. Plot `ln t½` against
> `ln c0`, fit the slope, read `n = 1 - slope`, then back out `k` from the integrated rate
> law for that order.

It charges the reactor at six concentrations from 5e-4 to 1.6e-2 mol/L — millimolar to
centimolar, geometrically spaced, a decade and a half wide. This is a *good* bench run by
ordinary standards: it is the concentration range where real reactors operate, the spacing
is right, and it uses the full budget.

It gets:

| `c0` (mol/L) | `t½` (s) |
|---|---|
| 5e-4 | 31.83 |
| 1e-3 | 31.65 |
| 2e-3 | 31.20 |
| 4e-3 | 30.27 |
| 8e-3 | 28.57 |
| 1.6e-2 | 25.67 |

Least-squares slope: **−0.0582**, so apparent order **n = 1.058**. A fractional order of
1.06 has no mechanistic meaning and sits comfortably within the scatter of any real
instrument, so the shortcut does the only sensible thing and calls it first order. Then
`k = ln2 / mean(t½) = 0.0232 s⁻¹`.

**Submitted:** `k0 = 0, k1 = 0.0232, k2 = 0`. **Wrong**: `k1` is +7.95%, and two of the three
channels have been asserted to be absent.

---

## Why it fails

The true law is `-d[A]/dt = k0 + k1[A] + k2[A]²`. The shortcut's window, 5e-4 to 1.6e-2
mol/L, sits almost exactly on the **maximum of the half-life curve** (the peak is at
c0 = 3.93e-4). Near a maximum, any smooth function is flat. The flatness the shortcut
measured is a property of *where it looked*, not of the chemistry.

This is the precise defect, and it is a general one:

> **A locally flat half-life is evidence about the neighbourhood, not about the mechanism.**
> `t½ ∝ c0^(1-n)` is a statement about a *single-term* rate law. Applied to a sum of terms,
> the fitted exponent is not an order — it is a local logarithmic derivative, and it takes
> whatever value the window makes it take.

The fitted "order" is therefore window-dependent, and demonstrably so:

| window fitted | apparent order `n` |
|---|---|
| 1e-3 … 1e-1 | 1.20 |
| 1e-6 … 1e2 | 1.33 |
| 1e-4 … 1e2 | 1.53 |
| 5e-4 … 1.6e-2 (the shortcut's) | 1.06 |

Four windows, four different orders, none of them real. A quantity that changes when you
change where you measure it is not a property of the system. That inconsistency is the tell,
and it is only visible to someone who probed more than one window.

Over twelve decades the truth is not subtle. The half-life is **non-monotonic**: it rises
with slope +1 below 1e-6 (zero-order floor), turns over near 4e-4, and falls with slope −1
above 1e-1 (second-order tail). No single power law produces a non-monotonic half-life, for
any `n` whatsoever. One probe at 1e-9 and one at 1e3 destroy the first-order hypothesis
outright — and the shortcut had six queries to spend and spent none of them there.

The shortcut's own answer refutes it, too, if extrapolated: a first-order law with
`k = 0.0232` predicts `t½ = 29.9 s` at every concentration, including `c0 = 1e-9`, where the
bench actually reads **0.01351 s** — wrong by a factor of 2200. The shortcut never checks,
because within its window there is nothing to check against.

---

## Why this trap is fair, not rigged

The requirement is that a *competent* naive solver fails for a *principled* reason. Auditing
the shortcut against that standard:

- **It is not crippled.** It uses the full 6-query budget, a correct least-squares fit, the
  correct half-life scaling law, and the correct integrated rate law for the order it infers.
  Every step is executed properly. Fix any "bug" in it and the answer does not improve,
  because there is no bug — there is a wrong model.
- **Its probe choice is the natural one.** Millimolar-to-centimolar is where chemistry is
  done. Choosing it is good laboratory instinct, and here good instinct is exactly what
  loses. The task punishes convenience, not incompetence.
- **A slightly smarter shortcut still fails, and this was checked.** Widening the probes to
  1e-4 … 1e3 — genuinely wide, six decades — recovers `k1` to +0.97% and `k2` to −0.14%,
  *both inside tolerance*, and still reports `k0 = 0`. That submission looks like a pass and
  is not. Widening further, to a correct three-term fit over 1e-3 … 1e2, pins `k1` and `k2`
  to 0.001% and still puts `k0` at **+3.0%**, because below 0.2% of the rate the zero-order
  channel is beneath what a 4-significant-figure instrument can resolve. The failure is
  informational, not computational: that data does not contain `k0`, and no better fitting
  extracts it.
- **The escape is available and cheap.** One query at the bottom of the stated charging
  range converts `k0` from ±10% to ±0.06%. The range is stated in `problem.md`, `help()`
  says in plain words that clustered readings constrain the chemistry less than they appear
  to, and the budget is ample for two probes per decade-extreme. Nothing is hidden. The
  solver simply has to decide that the edges of the range are worth two of six queries.
- **Being right about the structure is not enough.** Even a solver who names the mechanism
  correctly — "zero-, first- and second-order channels in parallel" — fails if they then
  quote `ln2/t½` for `k1`. The best such reading available anywhere in the domain is +1.29%,
  outside the 1% tolerance. The last step of the task refuses to be approximated.

---

## The one-line summary

The shortcut mistakes **the flatness of a curve near its maximum** for **the concentration-
independence of a first-order half-life**. They look identical through a narrow window and
are unrelated facts. The only defence is to open the window.
