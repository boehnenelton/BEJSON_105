#!/bin/bash
# usage: runts.sh <Lib_TS/Core dir> <outdir>   -> compiles (typechecked, strict) index.ts + tests to outdir, runs every test
CORE="$1"; OUT="$2"
rm -rf "$OUT"; mkdir -p "$OUT"
TR="${TS_TYPES_ROOT:?set TS_TYPES_ROOT to a node_modules/@types directory that contains the node typings}"
cd "$CORE" || exit 1
tsc --target es2020 --module commonjs --moduleResolution node10 --ignoreDeprecations 6.0 --ignoreConfig --skipLibCheck --strict --types node --typeRoots $TR --outDir "$OUT" index.ts tests/*.ts 2>&1 | head -30
echo "tsc exit: ${PIPESTATUS[0]}"
for f in "$OUT"/tests/*.js; do
  r=$(cd "$OUT/tests" && timeout 120 node "$f" 2>&1 | tail -3 | tr '\n' ' ')
  echo "$(basename $f): ${r:0:200}"
done
