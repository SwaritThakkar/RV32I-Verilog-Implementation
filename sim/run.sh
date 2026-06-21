#!/usr/bin/env bash
# Build and run the RV32I processor testbench with Icarus Verilog.
# Usage: bash sim/run.sh   (run from the repository root or anywhere)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT="sim/rv_sim"

echo ">> Compiling rtl/riscv_processor.sv + tb/testbench.sv"
iverilog -g2012 -o "$OUT" rtl/riscv_processor.sv tb/testbench.sv

echo ">> Running simulation"
vvp "$OUT" | tee sim/sim.log

rm -f "$OUT"
echo ">> Transcript written to sim/sim.log"
