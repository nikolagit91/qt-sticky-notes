#!/bin/bash
# Puni prolaz test suitea. Pokretanje iz korijena repoa:
#   sticky_notes_tests/run_all.sh
# Exit 0 = sve zeleno (test_x11_symbols.py je poznat okolinski FAIL pod
# offscreenom SAMO kad izlaz sadrži X11 potpis BadWindow — tada se ne
# računa kao pad, ispiše se kao SKIP-FAIL. Svaki drugi pad tog fajla
# (ili bilo kojeg drugog) je pravi FAIL.
set -u
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH="$PWD"
export LC_ALL=C

known_env_fail="test_x11_symbols.py"
known_env_fail_signature="X Error of failed request:  BadWindow (invalid Window parameter)"
pass=0; fail=0; envfail=0
failed_names=()
failed_logs=()
total_start=$(date +%s%3N)

for f in sticky_notes_tests/tests/test_*.py sticky_notes_tests/tests/golden_suite.py; do
  name=$(basename "$f")
  log="/tmp/sn_test_${name%.py}.log"
  s=$(date +%s%3N)
  if dbus-run-session -- python3 -u "$f" > "$log" 2>&1; then
    st="PASS"; pass=$((pass+1))
  elif [ "$name" = "$known_env_fail" ] && grep -qF "$known_env_fail_signature" "$log"; then
    st="SKIP-FAIL (okolinski)"; envfail=$((envfail+1))
  else
    st="FAIL"; fail=$((fail+1)); failed_names+=("$name"); failed_logs+=("$log")
  fi
  e=$(date +%s%3N)
  printf "%-46s %-22s %5d ms\n" "$name" "$st" "$((e-s))"
done

total_end=$(date +%s%3N)
echo "------------------------------------------------------------"
printf "UKUPNO: %d PASS, %d FAIL, %d okolinski — %d.%01d s\n" \
  "$pass" "$fail" "$envfail" "$(((total_end-total_start)/1000))" "$((((total_end-total_start)%1000)/100))"
if [ "$fail" -gt 0 ]; then
  echo "PALI:"
  for i in "${!failed_names[@]}"; do
    printf "  %s — log: %s\n" "${failed_names[$i]}" "${failed_logs[$i]}"
  done
  exit 1
fi
exit 0
