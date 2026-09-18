# Download diagnostic plan
Three environments only, each with matched data and Blob downloads of expected.json.
A: manual CDP allowAndName with forward slash downloadPath.
B: versus A, only CDP downloadPath uses native Windows separators.
C: versus A, omit manual CDP download configuration; Playwright alone manages.
All other launch/network/security settings held constant apart from isolated directories. Per operation <=20s; total <=180s. No reference edits or acceptance steps beyond 9.
