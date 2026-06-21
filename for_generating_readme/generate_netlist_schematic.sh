#!/usr/bin/env bash
# Generate the synthesized-RTL netlist schematic (the README hero).
#
# Pipeline (all premade EDA tooling):
#   Yosys      — read the Verilog, elaborate, and emit the RTL netlist as a
#                Graphviz .dot (cells = $add/$sub/$mux/$dff/$mem/... operators)
#   Python     — re-theme the .dot: dark background, colour cells by operator,
#                gold I/O pins, glowing nets
#   Graphviz   — lay the netlist out with the sfdp force-directed engine
#                (packs the graph into a dense, roughly-square "constellation")
#   rsvg-convert — rasterise the SVG to a high-resolution PNG
#
# Requirements: yosys, graphviz (sfdp), librsvg (rsvg-convert), python3.
# Usage: bash for_generating_readme/generate_netlist_schematic.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="for_generating_readme"
TMP="$(mktemp -d)"

echo ">> [1/4] Yosys: synthesize RTL -> Graphviz dot"
yosys -q -p "
  read_verilog -sv rtl/riscv_processor.sv
  hierarchy -top riscv_processor
  proc
  opt -noff
  memory_collect
  opt_clean
  show -format dot -prefix $TMP/rv -width -notitle
"

echo ">> [2/4] Python: apply dark EDA theme + colour cells by operator"
python3 - "$TMP/rv.dot" "$TMP/rv_dark.dot" <<'PY'
import re, sys
src = open(sys.argv[1]).read()

def style(t):
    arith = {'$add','$sub','$shl','$shr','$sshr','$mul'}
    logic = {'$and','$or','$xor','$not','$reduce_or','$reduce_bool','$reduce_and'}
    comp  = {'$eq','$ne','$lt','$le','$gt','$ge','$logic_and','$logic_or','$logic_not'}
    mux   = {'$mux','$pmux'}
    if t in arith: return ('#10243d', '#FACC15')
    if t in logic: return ('#0e1f33', '#60A5FA')
    if t in comp:  return ('#1E1B4B', '#818CF8')
    if t in mux:   return ('#172033', '#A5B4FC')
    if t == '$dff':return ('#123524', '#6EE7B7')
    if t == '$mem':return ('#3B1D0B', '#F97316')
    return ('#111827', '#64748B')

def color_cell(m):
    head, label = m.group(1), m.group(2)
    tm = re.search(r'\\n(\$\w+)', label)
    fill, border = style(tm.group(1) if tm else '')
    return (f'{head} [ shape=record, style="filled,rounded", fillcolor="{fill}", '
            f'color="{border}", fontcolor="#E6EAF7", penwidth=1.8, label="{label}" ];')

src = re.sub(r'(c\d+) \[ shape=record, label="(.*?)",\s*\];', color_cell, src)
src = src.replace('color="black", fontcolor="black"', 'color="#5b6b8c", fontcolor="#cdd6f4"')
src = src.replace('fontcolor="black"', 'fontcolor="#cdd6f4"').replace('color="black"', 'color="#5b6b8c"')
src = re.sub(r'shape=octagon, label="([^"]+)", color="#5b6b8c", fontcolor="#cdd6f4"',
             r'shape=octagon, style=filled, fillcolor="#0B1020", color="#FFD34D", '
             r'fontcolor="#FFE8A3", penwidth=2.0, label="\1"', src)

inject = ('\n  bgcolor="#070A12";\n  layout=sfdp;\n  overlap=prism;\n'
          '  overlap_scaling=-4;\n  splines=true;\n  K=1.1;\n  repulsiveforce=1.4;\n'
          '  nodesep=0.25;\n  ranksep=0.6;\n  pad=0.5;\n'
          '  node [fontname="Helvetica", fontsize=12];\n'
          '  edge [color="#6b8bd4", penwidth=2.3, arrowsize=0.7];\n')
src = src.replace('rankdir="LR";', 'rankdir="LR";' + inject, 1)
open(sys.argv[2], 'w').write(src)
print("   themed dot written")
PY

echo ">> [3/4] Graphviz sfdp: force-directed layout -> SVG"
sfdp -Tsvg "$TMP/rv_dark.dot" -o "$OUT/rtl_netlist_yosys.svg"

echo ">> [4/4] rsvg-convert: high-resolution PNG"
rsvg-convert -w 3400 "$OUT/rtl_netlist_yosys.svg" -o "$OUT/rtl_netlist_yosys.png"

rm -rf "$TMP"
echo ">> Wrote $OUT/rtl_netlist_yosys.{svg,png}"
