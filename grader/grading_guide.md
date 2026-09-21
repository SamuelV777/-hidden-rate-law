# grading_guide.md — How to grade, and the near-misses that must not pass

> Grading is defined **against the locked answer in `STATE.md` / `golden/expected.json`**.
> It was written before `problem.md` existed and is never reverse-engineered from the prompt.

---

## 1. The locked answer

    -d[A]/dt = k0 + k1*[A] + k2*[A]^2

| Coefficient | Locked value | Units |
|---|---|---|
| `k0` | 3.7e-8 | mol/(L*s) |
| `k1` | 2.15e-2 | 1/s |
| `k2` | 0.48 | L/(mol*s) |

## 2. The grading rule

A submission **PASSES** if and only if all four hold:

1. `|k0_sub/3.7e-8 - 1| <= 0.01`
2. `|k1_sub/2.15e-2 - 1| <= 0.01`
3. `|k2_sub/0.48 - 1| <= 0.01`
4. every reported coefficient of degree 3 or higher is zero

Anything else **FAILS**. There is no partial credit: recovering two of three coefficients is
not a partial recovery of the rate law, it is a different rate law. A law missing its
zero-order term mispredicts the half-life at `c0 = 1e-9` by a factor of ~2400; a law missing
its second-order term mispredicts at `c0 = 1e3` by a factor of ~15000. These are not close.

**Why 1% and not 5%.** See `STATE.md` section 5. The short version: the best reading the
textbook first-order approximation can possibly yield is `k1 = 0.0217765`, which is +1.29%.
A 5% tolerance would pass a solver who never modelled the system at all. 1% is the largest
tolerance that still forces the solver to integrate the rate law, and it leaves an honest
solver a 10x margin (a correct wide-probe fit lands within ~0.1%).

**Units are part of the answer.** A coefficient reported in mmol, minutes, or per-mole-per-
litre-inverted is wrong, not close. The tolerance is not a units amnesty.

---

## 3. Near-miss table

Every row below is a wrong answer that a real solver actually lands on. Each was produced by
running the stated procedure against the real oracle readings — these are measured outcomes,
not invented ones.

| # | Near-miss submission | How a solver gets here | Precise reason it is wrong |
|---|---|---|---|
| 1 | `k0=0, k1=0.0232, k2=0` | Probes a one-decade ladder (5e-4 … 1.6e-2), sees half-lives 31.83 → 25.67, judges them "roughly constant", applies `t½ = ln2/k` | **The headline trap.** Half-life constancy over one decade is not evidence of first order; it is what *any* rate law looks like near the maximum of its half-life curve. `k1` is +7.95% and both other terms are asserted to be zero on no evidence. |
| 2 | `k0=0, k1=0.0217765, k2=0` | Same reflex, but disciplined: takes the single largest half-life (31.83 s at the curve's peak) as the cleanest plateau reading | The *best possible* first-order reading, and still **+1.29%** — outside tolerance. There is no `c0` anywhere in the domain at which `ln2/t½` is accurate to 1%, because the true peak (31.8368 s) never reaches `ln2/k1` (32.2394 s). Fails on `k1` as well as on the two zeroed terms. |
| 3 | `k0=3.81e-8, k1=0.0215, k2=0.480` | Correct three-term structure, correct integration, correct least-squares — but all six probes placed in "sensible laboratory" range (1e-3 … 1e2) | **The most dangerous near-miss.** `k1` and `k2` are recovered to 0.001%. `k0` comes out **+3.00%** and fails. At `c0 >= 1e-3` the zero-order term contributes under 0.2% of the rate, which is below what a 4-significant-figure instrument can resolve. The data is genuinely insufficient — no better fitting rescues it. Only a probe near the bottom of the stated range does. |
| 4 | `k0=0, k1=0.0217076, k2=0.4793` | Probes 1e-4 … 1e3 — wide, but never below 1e-4 — then fits a two-term law because the data shows no floor | `k1` lands at +0.966% and `k2` at −0.143%, **both inside tolerance**, so this submission looks like a pass and is not. The zero-order channel is missed entirely. Wide probing is not the same as probing the extremes. |
| 5 | `k0=3.696e-8, k1=0.0217069, k2=0` | The mirror error: probes 1e-9 … 1e-3, finds the floor and the flat region, never reaches the second-order regime | `k0` to −0.107% and `k1` to +0.962%, again two of three inside tolerance. Fails on `k2`. |
| 6 | `rate = k*[A]^1.20` | Fits a single power law to `t½` vs `c0` over 1e-3 … 1e-1 and reads the apparent order off the slope | Wrong model class. A fractional apparent order is an artifact of superposing integer-order channels, not a physical order. The fitted exponent is window-dependent — 1.20, 1.53, or 1.33 depending on where you look — which is itself the tell that no single power law exists. |
| 7 | `rate = k*[A]^1.53` | Same, over the wider window 1e-4 … 1e2 | Same defect. Worth listing separately because a solver who probes *more* widely and still fits one power law gets a *worse* exponent, and may read that as bad data rather than a wrong model. |
| 8 | `k0=3.7e-5, k1=0.0215, k2=0.48` | Correct physics, reports `k0` in mmol/(L*s) | Unit slip, ×1000. Wrong. The instrument's concentrations are mol/L and its times are seconds; the coefficients inherit those units. |
| 9 | `k0=3.7e-8, k1=0.0215, k2=4.8e-4` | Correct physics, reports `k2` in L/(mmol*s) | Unit slip, ×0.001. Wrong. |
| 10 | `k0=3.7e-8, k1=0.0727, k2=0.48` | Misreads the observable as the time to fall to 10% of `c0` and uses `ln10/t` | +238% on `k1`. The instrument returns a **half**-life; the definition is stated in the prompt and is not negotiable. |
| 11 | `k0=3.7e-8, k1=0.0215, k2=0.48, k3=5e-8` | Fits degree 3 because an extra free parameter always reduces residuals | Fails rule 4 — **and this row needs grading care, because the data does not refute it.** Any `k3` below ~5e-7 reproduces every reading inside the instrument's rounding floor (at `c0 = 1e3` such a term is 0.0104% of the rate). It is excluded by the parsimony rule stated in `problem.md` — report the lowest degree consistent with the readings — not by the evidence. Grade it as a failure, and if a solver protests that their law fits, they are right that it fits and wrong that fitting was the criterion. Note the lower coefficients will look correct: across the whole unfalsifiable band they shift by at most 0.02%. |
| 12 | `k0=3.9e-8, k1=0.0208, k2=0.472` | Used the oracle's undocumented noisy sampling surface as if it were a measurement channel and fitted the noise | The noisy surface is seeded and reproducible, which makes wrong answers derived from it *consistent* across reruns and therefore convincing. It is a cost trap: it spends budget and returns degraded data. Errors of a few percent across all three coefficients are its signature. |

---

## 4. What a passing submission looks like

    k0 = 3.7e-8   mol/(L*s)      (within 1%)
    k1 = 2.15e-2  1/s            (within 1%)
    k2 = 0.48     L/(mol*s)      (within 1%)
    degree 2, no higher terms

Reached by: probing at or below ~1e-8 to expose the zero-order floor, at or above ~1e2 to
expose the second-order tail, and at least once in the 1e-4 … 1e-2 region to constrain the
first-order channel — then integrating `1/(k0 + k1*c + k2*c^2)` from `c0/2` to `c0` and
solving for the three coefficients against all readings. Asymptotics alone give `k0` to 0.04%
and `k2` to 0.008%; only `k1` requires the full inversion.

---

## 5. Grader failure modes to watch for

- **Do not reward structure without values.** "It is a mixed-order decay with zero-, first-
  and second-order channels" is the right insight and not the answer. Rows 3–5 all have the
  right structure and all fail.
- **Do not reward two-of-three.** Rows 4 and 5 each have two coefficients inside tolerance.
  Both are failures. Check all three, every time.
- **Do not accept a relative-error pass on a mislabelled unit.** Check the units string, then
  the number.
- **Do not let a reported `k3 ~ 1e-4` slide as "negligible".** Rule 4 is exact: zero or fail.
