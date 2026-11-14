# Cross-language conformance harness
Generates a corpus from the Python reference (`gen.py`) and replays it through the JS, TS and SH validators. Contract: same valid/invalid verdict, and the same MFDB spec codes [30]-[41] whenever the reference emits one. Entities that fail base BEJSON validation are compared by verdict only. FK audit: same findings (code|entity) plus same strict-FK verdict.
Run from this folder (paths are examples; edit `runts.sh` TR= to your @types/node):
    CORE=../../Lib_PY/Core CORPUS=./corpus python3 -I gen.py
    python3 -I drv.py ../../Lib_PY/Core ./corpus
    node drv.js ../../Lib_JS/Core ./corpus
    bash drv_sh.sh ../../Lib_SH/Core ./corpus
    bash runts.sh ../../Lib_TS/Core /tmp/ts_out && node drv_ts.js /tmp/ts_out ./corpus
    (FK) python3 -I drv_fk.py ... | node drv_fk.js ... | node drv_fk_ts.js /tmp/ts_out ./corpus | bash drv_fk.sh ...
Known cosmetic: JS emits fewer advisory UUID warnings than Python on already-invalid files.
