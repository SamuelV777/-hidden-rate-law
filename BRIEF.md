# BRIEF.md — Top-down summary

> **Leak discipline.** This file is written to survive an adversarial read. It names no
> coefficient, no value, no term count, and no property of the hidden curve that would
> shorten the investigation. Anyone who reads it learns the *shape* of the task and nothing
> about its answer. The mechanism, the uniqueness proof and the difficulty analysis live in
> `STATE.md`, which is authoring-side only.

**Domain:** STEM -> Chemistry (chemical kinetics).

---

## The hidden system

A black-box reaction bench holds an isothermal, constant-volume batch reactor containing a
single decaying species **A**. The instantaneous consumption rate of A is a fixed function of
its current concentration, and that function is what is hidden.

The bench does **not** report a rate. It reports a **half-life**: the solver charges the
reactor to an initial concentration of their choosing and the bench returns how many seconds
it takes for the concentration to fall to half of that. Readings are exact and reproducible,
quoted to a fixed number of significant figures.

That one design choice — reporting an integrated quantity rather than a differential one — is
what makes the task an investigation rather than a calculation. A rate reading would expose
the rate law almost directly. A half-life reading exposes only a smeared functional of it.

## What the solver must recover

The coefficients of the hidden rate law, modelled as a polynomial in [A] with non-negative
coefficients. **The degree is not disclosed**; determining it is part of the work. The solver
reports the coefficients as a machine-readable list in stated units.

Grading is by relative error against the locked answer, with a tolerance chosen so that it
cannot be met by approximation — only by integrating the candidate rate law and inverting it.
The tolerance, and the arithmetic justifying it, are in `STATE.md` section 5.

## The probing surface

| Surface | Cost |
|---|---|
| `evaluate(c0)` — half-life at initial concentration `c0` | 1 query |
| `help()` — a free methodological note that reveals nothing about the answer | free |

**Query budget: 6.** The admissible range of `c0` spans twelve decades. Six queries against
twelve decades is the whole tension of the task: the solver cannot sweep, cannot bisect
blindly, and cannot afford a cluster of redundant probes. Every query has to be placed for
information rather than for convenience, and the task is designed so that the difference
between those two is decisive rather than marginal.

The oracle carries a third surface that the solver-facing prompt does not advertise. It is
seeded and reproducible. It is a cost trap, not a shortcut.

## The reasoning trap

The naive approach is not a strawman. It is a standard, correctly-executed textbook procedure
— the first thing a competent chemist would reach for — applied to a data set that a
competent chemist would think was a good one. It produces a confident, self-consistent and
wrong answer, and it fails for a principled reason rather than through any error in its own
arithmetic. Documented in `reasoning_trap.md`.

## Difficulty target

A strong model at 8 attempts should land **<= 2/8**.

The difficulty is not arithmetic; every number in this task is easy to compute once you know
what to compute. It comes from three independent gates, each of which is separately
sufficient to fail an attempt: one about where evidence is gathered, one about what model is
fitted to it, and one about whether the final step is approximated or solved. They are
enumerated with supporting measurements in `STATE.md` and reported by
`python scripts/checks.py preview`.

## Artifact map

| File | Role | Side |
|---|---|---|
| `STATE.md` | locked answer, uniqueness proof, tolerance justification | authoring |
| `golden/expected.json` | locked answer, machine-readable | authoring |
| `grader/grading_guide.md` | near-miss table | authoring |
| `reasoning_trap.md` | why the naive approach fails, and why that is principled | authoring |
| `BRIEF.md` | this file | authoring |
| `oracle/oracle.py` | the hidden system | callable, not readable |
| `solution/main.py` | intended solver — PASSES within budget | authoring |
| `solution/shortcut.py` | naive solver — FAILS | authoring |
| `scripts/checks.py` | calibration harness | authoring |
| `problem.md` | solver-facing prompt — written last | **solver** |

Only `problem.md` and the callable surfaces of `oracle/oracle.py` are solver-facing.
