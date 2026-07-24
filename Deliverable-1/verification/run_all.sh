#!/usr/bin/env bash
# run_all.sh — reproduce every piece of verification evidence and capture it under results/.
# Usage:  bash verification/run_all.sh      (from the Deliverable-1 root)
# Requires: python3 only. No install, no network, no services.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="verification/results"
mkdir -p "$OUT"

echo "== unit tests =="
python3 -m unittest discover -s implementation/tests -v > "$OUT/unit_tests.txt" 2>&1
echo "   exit=$? -> $OUT/unit_tests.txt"

echo "== compile check =="
python3 -m py_compile implementation/mnemo/*.py implementation/gates/*.py implementation/eval/*.py \
  > "$OUT/compile.txt" 2>&1
echo "   exit=$? -> $OUT/compile.txt"

echo "== gates G0-G4 =="
: > "$OUT/gates.txt"
for g in g0_isolation g1_pii g2_baseline g3_lifecycle g4_observability; do
  {
    echo "########## gate_$g ##########"
    python3 "implementation/gates/gate_$g.py"
    echo "exit=$?"
    echo
  } >> "$OUT/gates.txt" 2>&1
  printf "   gate_%-16s captured\n" "$g"
done

echo "== evaluations =="
python3 implementation/eval/run_comparison.py > "$OUT/comparison.txt" 2>&1
python3 implementation/eval/run_3arm.py       > "$OUT/three_arm.txt"  2>&1
echo "   -> $OUT/comparison.txt, $OUT/three_arm.txt"

echo "== evaluation dataset =="
python3 verification/build_evaluation_dataset.py > "$OUT/dataset_build.txt" 2>&1

echo "== independent verification (§8.3) =="
python3 verification/verify.py > "$OUT/verify.txt" 2>&1
VERIFY_EXIT=$?
echo "   exit=$VERIFY_EXIT -> $OUT/verify.txt (+ verification_results.json, summary.txt)"

echo
echo "ALL EVIDENCE CAPTURED IN $OUT"
exit $VERIFY_EXIT
