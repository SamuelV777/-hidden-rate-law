# The RB-7 Reaction Bench

## The situation

A sealed reaction bench sits in front of you. Inside is an isothermal, constant-volume batch
reactor charged with a single decaying species, **A**.

The bench's calibration records were lost. What is known — and confirmed by the instrument's
own notes — is that the consumption rate of A depends only on the current concentration of A
and on nothing else: no temperature programme, no second reagent, no induction period, no
back reaction. The chemistry is a fixed function of `[A]`.

Your job is to recover that function.

## What the bench will tell you

You may charge the reactor to an initial concentration of your choosing and read off the
**half-life** of A: the elapsed time, in seconds, for `[A]` to fall from that initial value
to one half of it.

```python
import sys
sys.path.insert(0, "oracle")
import oracle

oracle.help()          # instrument notes. free.
oracle.evaluate(c0)    # half-life in seconds at initial concentration c0 mol/L. costs 1.
```

| | |
|---|---|
| **Charging range** | `c0` from `1e-9` to `1e3` mol/L |
| **Rated precision** | 4 significant figures |
| **Run budget** | **6 loadings** |

Readings are exact and reproducible: the same `c0` always returns the same number. Charging
to a concentration you have already used spends a unit of budget and teaches you nothing.
`oracle.help()` is free and may be called at any time.

The budget is six. It is not six per attempt, or six per idea — six in total. Spend them on
purpose.

## What to recover

Model the consumption rate of A as a polynomial in `[A]` with non-negative coefficients:

```
-d[A]/dt  =  sum over i >= 0 of  k_i * [A]^i
```

**The degree is not given to you.** Determining how many terms the rate law actually has is
part of the problem, and so is determining which of them are genuinely present rather than
merely permitted.

**Report the lowest degree consistent with your readings.** The bench quotes 4 significant
figures. A term whose contribution stays below that precision everywhere in the charging
range is not a term your data supports — it is one your data merely tolerates, and there are
infinitely many of those. Adding one will always reduce your residuals and will always be
wrong. The test to apply before you submit: drop the highest term and refit. If every reading
is still reproduced to the precision the bench quotes, the term was not earned — leave it
out. Keep it only if dropping it visibly breaks a reading.

Concentrations are in mol/L and times are in seconds, so `k_i` carries units of
`mol^(1-i) * L^(i-1) * s^-1` — that is, `mol/(L*s)` for `i = 0`, `1/s` for `i = 1`,
`L/(mol*s)` for `i = 2`, `L^2/(mol^2*s)` for `i = 3`, and so on up the series.

## Submitting

Print a single JSON object on stdout:

```json
{
  "degree": 3,
  "coefficients": [0.0, 1.5e-3, 0.0, 2.7]
}
```

`coefficients` is the full list in **ascending** order of power, from `i = 0` up to
`i = degree`, in the units above. Include every coefficient up to the degree you claim,
zeros included. The example above is a formatting illustration only — it is not a hint about
this bench.

## How you will be graded

Every coefficient you report must be within **1% relative error** of the true value, and the
degree you claim must be the true degree — a rate law with a spurious extra term is wrong
even if its lower coefficients are good.

There is no partial credit. A rate law with even one coefficient wrong is not a partial
recovery of the chemistry; it is a different reaction, and it will mispredict the bench by
orders of magnitude somewhere in the charging range.

1% is a deliberate choice. The readings are exact to 4 significant figures and the reactor is
noiseless, so the tolerance is not there to absorb measurement error — there is none to
absorb. It is there to mark the difference between a coefficient you have determined and a
coefficient you have estimated. Standard closed-form approximations from a kinetics textbook
will not clear it. Verify any number you are about to submit by predicting a reading you
have already taken, and check that the prediction matches to the precision the bench quotes.

## Ground rules

- Use `oracle.evaluate` and `oracle.help` only. Do not read, import internals from, decompile,
  or otherwise inspect the contents of `oracle/oracle.py`; the trim table inside it is not
  part of the evidence you are given, and recovering the answer from the source rather than
  from the bench does not count as solving anything.
- Python standard library only. Offline. No network, no API keys, no third-party packages.
- Stay inside the charging range. The bench will refuse a loading outside it, and a refused
  loading is still a loading you planned badly.
