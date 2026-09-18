"""Predicted step-level failure lists for single mutants and the defective
combo, derived from the frozen mutation-map v0.1 witness table plus the case
step structure in cases.py.

Derivation notes (disclosed in the fabrication log / final report):
- U01 steps "2"/"9" of the frozen public-cases are encoded here as 2a/2b/2c
  and 9a/9b (each command is one step); granularity is otherwise identical.
- The fabrication spec §3 table describes impact as "D1: U01 步1/3、U05;
  D3: U01 步7–9、U09 步5/6", while the frozen mutation-map §3 says U09
  步骤3/5/6. Neither is meant to be an exhaustive step list: the map fixes
  witnesses + controls, and this artifact fixes the exhaustive list. Three
  corrections vs the first draft of this file (found by the evaluator itself
  during calibration, mut-cal-1):
    (a) under M01, U01 steps 2a-2c also fail: t1 is corrupted at step 1 and
        every later accumulated-store semantic assertion includes t1;
    (b) under M01, U05 step 3 also fails: the query still matches, but the
        JSON output-value assertion includes the corrupted body;
    (c) under M03 alone, U01 step 9b PASSES: the on-disk array
        [t4,t3,t2,t1,t5] re-reverses on load, restoring t2 before t3.
- Single-mutant lists are exhaustive per case (stricter than the map's
  minimal witness sets); the defective list is the union and is checked for
  exact equality in both directions.
"""

M01_EXPECTED = {
    "U01": ["1", "2a", "2b", "2c", "3", "6", "7", "8", "9a"],  # t1 corrupted, persists
    "U05": ["1", "2", "3"],                                     # corrupted body in output
}

M02_EXPECTED = {
    "U01": ["4", "9b"],                       # strasse query misses Straße/STRASSE二
    "U04": ["1", "2", "3"],                   # casefold collapse broken
}

M03_EXPECTED = {
    "U01": ["7", "8", "9a"],                  # array reload reversed (9b: double reversal)
    "U09": ["3", "5", "6"],                   # array add/list/export order
}

DEFECTIVE_EXPECTED = {
    "U01": ["1", "2a", "2b", "2c", "3", "4", "6", "7", "8", "9a", "9b"],
    "U04": ["1", "2", "3"],
    "U05": ["1", "2", "3"],
    "U09": ["3", "5", "6"],
    # controls: U02 U03 U06 U07 U08 U10 — every step passes
}

ALL_CASE_IDS = ["U01", "U02", "U03", "U04", "U05", "U06", "U07", "U08", "U09", "U10"]
