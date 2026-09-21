# STATE.md — Locked Answer (authoring-side only; never shown to the solver)

**Domain:** STEM -> Chemistry
**Status:** COMMITTED. Nothing downstream may alter these numbers.

---

## 1. The committed answer

The hidden system is an isothermal, constant-volume batch reactor consuming a single
species **A**. Its consumption rate depends only on the current concentration and is a
**three-term polynomial rate law**:

    -d[A]/dt  =  k0  +  k1*[A]  +  k2*[A]^2

| Parameter | Locked value | Units | Mechanistic reading |
|---|---|---|---|
| `k0` | **3.7e-8** | mol/(L*s) | zero-order floor (saturated catalyst / constant-flux photolysis) |
| `k1` | **2.15e-2** | 1/s | first-order unimolecular channel |
| `k2` | **0.48** | L/(mol*s) | second-order bimolecular channel |

Degree of the polynomial is **exactly 2**; all three coefficients are strictly positive.
There is no `k3` or higher term, and no coefficient is zero.

**Observable surface.** The instrument does not report the rate. `evaluate(c0)` returns the
**half-life** `t_half(c0)` -- the time in seconds for [A] to fall from `c0` to `c0/2` --
quoted to **4 significant figures**. The solver must invert an integrated rate law, not read
a rate off a slope.

    t_half(c0)  =  integral from c0/2 to c0 of  dc / (k0 + k1*c + k2*c^2)

Since the discriminant `k1^2 - 4*k0*k2 = 4.62179e-4 > 0`, this has the closed form

    t_half = [ ln|(c - rp)/(c - rm)| / (k2*(rp - rm)) ]  evaluated from c0/2 to c0
    rp, rm = ( -k1 +/- sqrt(k1^2 - 4*k0*k2) ) / (2*k2)        (both roots negative)

**Input domain:** `c0` in `[1e-9, 1e3]` mol/L (12 decades). **Query budget: 6.**

**Grading tolerance:** 1% relative error on each of `k0`, `k1`, `k2` (justified in section 5).

---

## 2. Order of design decisions (authoring trail)

1. **Chose the observable before the law.** Reporting `t_half` rather than rate forces the
   solver through an integration step, and sets up the single most seductive trap in
   kinetics: "half-life independent of `c0` implies first order".
2. **Chose a three-term law** so the curve has *three* asymptotic regimes rather than one
   power law. A one- or two-term law is recognisable from any two points; three regimes
   spread over 12 decades cannot be seen through a narrow window.
3. **Placed the crossovers ~4.4 decades apart** so each regime is cleanly reachable but no
   two are visible at once:
   - `c_lo* = k0/k1 = 1.721e-6`  (zero-order -> first-order)
   - `c_hi* = k1/k2 = 4.479e-2`  (first-order -> second-order)
4. **Chose the reporting precision last, from an identifiability calculation.** 4 significant
   figures is not decoration -- see section 5. It is what makes probe placement matter.
5. **Chose parameter values that are chemically plausible but not guessable** -- no round
   decades, no repeated mantissas, continuous-valued.

---

## 3. The signature of the hidden system

`t_half` is **non-monotonic** in `c0`. This is the key evidence, and it is invisible unless
the solver spans decades.

| `c0` (mol/L) | `t_half` (s, 4 s.f.) | dominant term | local log-log slope |
|---|---|---|---|
| 1e-9 | 0.01351 | `k0` | -- |
| 1e-8 | 0.1345 | `k0` | +1.00 |
| 1e-7 | 1.295 | `k0` | +0.98 |
| 1e-6 | 9.444 | `k0` | +0.86 |
| 1e-5 | 25.86 | `k1*[A]` | +0.44 |
| 1e-4 | 31.41 | `k1*[A]` | +0.08 |
| 1e-3 | 31.65 | `k1*[A]` | +0.00 |
| 1e-2 | 27.78 | `k1*[A]` | -0.06 |
| 1e-1 | 12.54 | `k2*[A]^2` | -0.35 |
| 1e0 | 1.952 | `k2*[A]^2` | -0.81 |
| 1e1 | 0.2069 | `k2*[A]^2` | -0.97 |
| 1e2 | 0.02082 | `k2*[A]^2` | -1.00 |
| 1e3 | 0.002083 | `k2*[A]^2` | -1.00 |

Peak: `c0 = 3.926e-4`, `t_half = 31.8368 s`. The peak lies **below** `ln2/k1 = 32.2394 s` and
never reaches it -- the plateau is an illusion that is always at least 1.26% low.

Asymptotics the intended solver exploits:

- `c0 -> 0`:   `t_half -> c0/(2*k0)`   slope **+1**, yields `k0`.
- middle:      `t_half -> ln2/k1`      slope **0**, approached but never attained.
- `c0 -> inf`: `t_half -> 1/(k2*c0)`   slope **-1**, yields `k2`.

---

## 4. Why this is the only answer

**Claim.** The function `c0 -> t_half(c0)` on `[1e-9, 1e3]` determines `(k0, k1, k2)`
uniquely within the declared class (polynomial rate law, non-negative coefficients).

**(a) The degree is forced from below, and fixed from above only by parsimony.**
For a rate law of degree `d` with leading coefficient `k_d`,
`t_half(c0) -> (2^(d-1) - 1) / ((d-1) * k_d * c0^(d-1))` as `c0 -> inf`, so the high-`c0`
log-log slope tends to `-(d-1)`. The observed slope is **-1.00** at both `c0 = 1e2` and
`c0 = 1e3`, which rules out every degree **below** 2: a pure degree-1 law would force slope 0,
a degree-0 law slope +1. So `d >= 2`, and that much the data does force.

It does **not** force `d <= 2`, and an earlier draft of this document wrongly claimed it did.
That argument took a `c0 -> inf` limit on a range bounded at `c0 = 1e3`. Measured properly
(`scripts/checks.py unique`), a degree-3 law reproduces all six spanning readings inside the
instrument's rounding floor for any

    k3  <~  5e-7  L^2/(mol^2*s)

because at the very top of the charging range such a term is only 0.0104% of the total rate
— an order of magnitude beneath what 4 significant figures resolve. No bounded range can fix
this: for any finite `c_max` there is always a `k3` small enough to hide, so widening the
range moves the threshold without removing it.

This costs the task nothing, because the hidden `k3` is *harmless to the recovered values*:
across the whole unfalsifiable band, re-optimising the lower coefficients moves them by at
most **0.02%**, versus a 1% tolerance. `k0`, `k1` and `k2` stay pinned regardless.

What closes the gap is therefore not the evidence but a stated criterion, and `problem.md`
states it explicitly as a rule the solver is graded against: *report the lowest degree
consistent with your readings; drop any term whose removal still reproduces every reading to
the bench's quoted precision.* That is ordinary model selection — the refusal to buy an extra
parameter with no evidence — and it is a skill the task is entitled to test, provided it is
asked for in the open rather than assumed. It is. Grading rule 4 rests on that sentence in
`problem.md`, not on a claim that the data refutes `k3`.

**(b) `k0` is forced.** `t_half/c0 -> 1/(2*k0)` exactly as `c0 -> 0`. At `c0 = 1e-9` the
first-order term contributes `k1*c0/k0 = 5.8e-4` of the rate, so the limit is attained to
0.03% -- resolvable at 4 s.f. No other `k0` reproduces the low-end readings.

**(c) `k2` is forced.** `c0*t_half -> 1/k2` exactly as `c0 -> inf`. At `c0 = 1e3` the
first-order term contributes `k1/(k2*c0) = 4.5e-5`, so the limit is attained to 0.005%.

**(d) `k1` is forced.** With `k0` and `k2` fixed, `t_half(c0)` is **strictly decreasing in
`k1`** for every `c0`: the integrand `1/(k0 + k1*c + k2*c^2)` is strictly decreasing in `k1`
pointwise on an interval of positive length. A strictly monotone map is injective, so a
single reading at any `c0` pins `k1`. Sensitivity is maximal near the peak, where
`dln(t_half)/dln(k1) ~= -0.96`.

**(e) Verified numerically, not merely argued.** A multi-start local search over
`(k0, k1, k2)` spanning `k0` x 10^+-1.5, `k1` x 10^+-0.5, `k2` x 10^+-0.5 found **no**
alternate triple reproducing the evidence, at either a mid-range or a wide probe set. The
only optimum is the true one. Re-runnable via `python scripts/checks.py unique`.

**(f) The answer is not brute-forceable.** Three strictly positive reals, each known a priori
only to within decades. There is no finite candidate set to sweep inside 6 queries; the
budget can only be spent on inference, never on enumeration.

---

## 5. Why the tolerance is 1% and the instrument quotes 4 significant figures

These two numbers were chosen together, from a profile-likelihood calculation, and they are
what make the task discriminating rather than merely fiddly.

**The instrument's precision creates the information floor.** 4 s.f. means a relative
rounding half-width of `5e-4`. Fixing `k0` at a wrong value and re-optimising `k1, k2`
against a probe set gives this best-achievable worst-case residual:

| probe set | `k0` x 0.9 | `k0` x 1.1 | verdict |
|---|---|---|---|
| mid-range only (1e-3 ... 1e2) | 2.8e-4 | 2.4e-4 | **below the floor -- indistinguishable** |
| wide (1e-8 ... 1e2) | 1.1e-1 | 9.0e-2 | 200x the floor -- pinned to ~0.06% |

A solver who probes only "sensible laboratory concentrations" **cannot** pin `k0` better than
about +-10%, no matter how good the fitting, and therefore fails. A solver who spends one
query at the bottom of the stated domain pins it to 0.06%. Probe placement is the skill being
tested, and the instrument precision is what makes it load-bearing.

**1% tolerance separates modelling from eyeballing.** The best possible plateau reading,
`ln2/t_half` taken exactly at the peak, gives `k1 = 0.0217719` -- **+1.26% high**, outside
tolerance. There is no `c0` at which the first-order approximation is good to 1%. The only
way to land inside 1% is to actually integrate the rate law. An honest solver using
asymptotics plus one exact inversion lands within ~0.1% -- a 10x margin. Hard, but fair.

---

## 6. What the solver must report

Three numbers: `k0`, `k1`, `k2`, in mol/(L*s), 1/s, and L/(mol*s) respectively. All three
must be within 1% relative error. Any claimed coefficient of degree 3 or higher must be zero.
