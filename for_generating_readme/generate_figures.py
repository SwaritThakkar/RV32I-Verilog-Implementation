#!/usr/bin/env python3
"""
generate_figures.py
===================
Regenerates the dark-themed raster figures used in README.md and
project_report.md. The architectural flowcharts (datapath, control FSM) are
authored as Mermaid blocks directly inside project_report.md; this script
produces the bit-field, table, timeline, and results plots that are clearer as
rasters.

Run from the repository root:

    python for_generating_readme/generate_figures.py

Outputs (written next to this script, in for_generating_readme/):

    instruction_formats.png      - RV32I instruction encoding formats
    supported_instructions.png   - table of the 37 implemented base instructions
    state_timeline.png           - cycle-by-cycle execution timeline
    test_results.png             - pass/fail summary across the testbench

The test_results figure is parsed from sim/sim.log if present; otherwise it
falls back to the committed reference numbers.

All figures share the project's dark "midnight" theme to stay visually
consistent with the Mermaid diagrams.
"""

import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------------------------------------------------------------------------
# Dark "midnight" theme — matches the Mermaid init directive palette
# ---------------------------------------------------------------------------
BG      = "#070A12"   # page background (near-black navy)
PANEL   = "#0F172A"   # panel / card background
CARD    = "#111827"   # neutral card fill
INK     = "#E6EAF7"   # primary text
MUTED   = "#9CA3AF"   # secondary text
GRID    = "#1f2a3d"   # gridlines / hairlines

BLUE    = "#60A5FA"   # fetch / datapath
PURPLE  = "#818CF8"   # decode / control
GREEN   = "#6EE7B7"   # pass / writeback
ORANGE  = "#F97316"   # memory
RED      = "#F43F5E"  # fail / blend
GOLD    = "#FACC15"   # highlight
SLATE   = "#64748B"   # immediate / neutral field

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "text.color": INK,
        "axes.labelcolor": INK,
        "axes.edgecolor": SLATE,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "figure.facecolor": BG,
        "axes.facecolor": BG,
        "savefig.facecolor": BG,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
    }
)


def glow_box(ax, x, y, w, h, text, fc, ec, fs=11, tc=INK, lw=1.6, rounded=0.05):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.0,rounding_size={rounded}",
        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2,
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, zorder=3, fontweight="bold")


def title(ax, text, x, y, fs=15):
    ax.text(x, y, text, ha="center", fontsize=fs, fontweight="bold",
            color=INK)


def save(fig, name):
    out = os.path.join(HERE, name)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {os.path.relpath(out, ROOT)}")


# ---------------------------------------------------------------------------
# 1. Instruction formats (bit fields)
# ---------------------------------------------------------------------------
def fig_formats():
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    ax.set_xlim(-3, 33)
    ax.set_ylim(-0.6, 13)
    ax.axis("off")
    title(ax, "RV32I Instruction Encoding Formats", 16, 12.2)

    rows = [
        ("R", [(7, "funct7", BLUE), (5, "rs2", PURPLE), (5, "rs1", PURPLE),
               (3, "funct3", BLUE), (5, "rd", GREEN), (7, "opcode", ORANGE)]),
        ("I", [(12, "imm[11:0]", SLATE), (5, "rs1", PURPLE),
               (3, "funct3", BLUE), (5, "rd", GREEN), (7, "opcode", ORANGE)]),
        ("S", [(7, "imm[11:5]", SLATE), (5, "rs2", PURPLE), (5, "rs1", PURPLE),
               (3, "funct3", BLUE), (5, "imm[4:0]", SLATE), (7, "opcode", ORANGE)]),
        ("B", [(7, "imm[12|10:5]", SLATE), (5, "rs2", PURPLE), (5, "rs1", PURPLE),
               (3, "funct3", BLUE), (5, "imm[4:1|11]", SLATE), (7, "opcode", ORANGE)]),
        ("U", [(20, "imm[31:12]", SLATE), (5, "rd", GREEN), (7, "opcode", ORANGE)]),
        ("J", [(20, "imm[20|10:1|11|19:12]", SLATE), (5, "rd", GREEN),
               (7, "opcode", ORANGE)]),
    ]

    # Fields listed MSB-first; drawn left-to-right so bit 31 is on the left and
    # the opcode (bits 6:0) lands on the right, matching the RISC-V spec.
    y = 10.2
    rh = 1.4
    for name, fields in rows:
        ax.text(-1.0, y + rh / 2, name + "-type", ha="right", va="center",
                fontsize=10.5, fontweight="bold", color=GOLD)
        x = 0.0
        for width, lbl, c in fields:
            ax.add_patch(Rectangle((x, y), width, rh, facecolor=c,
                                   edgecolor=BG, lw=1.6, alpha=0.92))
            ax.text(x + width / 2, y + rh / 2, lbl, ha="center", va="center",
                    fontsize=7.6, color="#0B1020", fontweight="bold")
            x += width
        y -= rh + 0.45

    for b in [31, 25, 20, 15, 12, 7, 0]:
        ax.text(31 - b + 0.5 if b else 31.6, y + 1.0, str(b),
                ha="center", fontsize=7.5, color=MUTED)
    ax.text(16, y + 0.05, "bit position  (31 ... 0)", ha="center",
            fontsize=8.5, color=MUTED)
    save(fig, "instruction_formats.png")


# ---------------------------------------------------------------------------
# 2. Supported instruction table
# ---------------------------------------------------------------------------
def fig_instr_table():
    groups = [
        ("Reg-Reg (R)", ["ADD", "SUB", "SLL", "SLT", "SLTU",
                          "XOR", "SRL", "SRA", "OR", "AND"], BLUE),
        ("Reg-Imm (I)", ["ADDI", "SLTI", "SLTIU", "XORI", "ORI",
                         "ANDI", "SLLI", "SRLI", "SRAI"], BLUE),
        ("Loads (I)", ["LB", "LH", "LW", "LBU", "LHU"], ORANGE),
        ("Stores (S)", ["SB", "SH", "SW"], ORANGE),
        ("Branches (B)", ["BEQ", "BNE", "BLT", "BGE", "BLTU", "BGEU"], GREEN),
        ("Jumps", ["JAL", "JALR"], PURPLE),
        ("Upper-imm (U)", ["LUI", "AUIPC"], GOLD),
    ]

    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")
    total = sum(len(v) for _, v, _ in groups)
    title(ax, f"Implemented RV32I Base Integer Instructions  ({total} total)",
          50, 47.5)

    x0 = 3.5
    colw = 13.4
    for title_txt, instrs, c in groups:
        glow_box(ax, x0, 39, colw - 1.2, 4.6, title_txt, PANEL, c, fs=8.6, tc=c)
        y = 36.5
        for ins in instrs:
            ax.add_patch(Rectangle((x0, y - 2.8), colw - 1.2, 2.5,
                                   facecolor=CARD, edgecolor=GRID, lw=1.0))
            ax.text(x0 + (colw - 1.2) / 2, y - 1.55, ins, ha="center",
                    va="center", fontsize=8.6, color=INK)
            y -= 3.0
        x0 += colw

    ax.text(50, 1.8,
            "ecall / ebreak intentionally excluded per the assignment specification.",
            ha="center", fontsize=8.6, color=MUTED, style="italic")
    save(fig, "supported_instructions.png")


# ---------------------------------------------------------------------------
# 3. Execution timeline
# ---------------------------------------------------------------------------
def fig_timeline():
    fig, ax = plt.subplots(figsize=(11.5, 4.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 40)
    ax.axis("off")
    title(ax, "Cycle-by-Cycle Execution  (state per clock)", 50, 37.8)

    seqs = [
        ("ALU / LUI / AUIPC", ["FETCH1", "FETCH2", "FETCH3", "DECODE", "EXEC", "WB"], GREEN),
        ("LOAD", ["FETCH1", "FETCH2", "FETCH3", "DECODE", "EXEC", "MEM1", "MEM2", "MEM3", "WB"], ORANGE),
        ("STORE", ["FETCH1", "FETCH2", "FETCH3", "DECODE", "EXEC", "MEM1", "MEM2", "MEM3"], ORANGE),
        ("BRANCH", ["FETCH1", "FETCH2", "FETCH3", "DECODE", "EXEC", "BRANCH"], BLUE),
        ("JAL / JALR", ["FETCH1", "FETCH2", "FETCH3", "DECODE", "EXEC", "JUMP"], PURPLE),
    ]
    cellw = 7.2
    x_start = 24
    for i in range(9):
        ax.text(x_start + i * cellw + (cellw - 0.6) / 2, 33.4, f"c{i+1}",
                ha="center", fontsize=7.8, color=MUTED, fontweight="bold")

    y = 28.5
    for name, states, c in seqs:
        ax.text(1, y + 1.4, name, fontsize=9, fontweight="bold", va="center",
                color=INK)
        x = x_start
        for st in states:
            ax.add_patch(Rectangle((x, y), cellw - 0.6, 3.0, facecolor=c,
                                   edgecolor=BG, lw=1.6, alpha=0.92))
            ax.text(x + (cellw - 0.6) / 2, y + 1.5, st, ha="center", va="center",
                    fontsize=6.3, color="#0B1020", fontweight="bold")
            x += cellw
        ax.text(x + 0.6, y + 1.5, f"{len(states)} cyc", fontsize=8.6,
                color=GOLD, va="center", fontweight="bold")
        y -= 4.8
    save(fig, "state_timeline.png")


# ---------------------------------------------------------------------------
# 4. Test results
# ---------------------------------------------------------------------------
def parse_sim_log():
    log = os.path.join(ROOT, "sim", "sim.log")
    if not os.path.exists(log):
        return None
    with open(log) as f:
        text = f.read()
    blocks = re.split(r"\nTest \d+:", text)
    names = re.findall(r"\nTest \d+:\s*(.+)", text)
    results = []
    for name, blk in zip(names, blocks[1:]):
        p = len(re.findall(r"\[PASS\]", blk))
        f_ = len(re.findall(r"\[FAIL\]", blk))
        results.append((name.strip(), p, f_))
    return results or None


def fig_test_results():
    results = parse_sim_log()
    if results is None:
        results = [
            ("ADD / SUB", 3, 0), ("AND / OR / XOR", 3, 0), ("SLT / SLTU", 3, 0),
            ("ADDI / ANDI / ORI / XORI", 4, 0), ("SLL / SRL / SRA", 3, 0),
            ("SLLI / SRLI / SRAI", 3, 0), ("LW / SW", 1, 0), ("LB / SB", 2, 0),
            ("LH / SH", 2, 0), ("Bxx (all 6)", 4, 0), ("JAL", 2, 0),
            ("JALR", 2, 0), ("LUI", 1, 0), ("AUIPC", 1, 0),
            ("Loop (sum 1..5)", 1, 0), ("Mixed program", 3, 0),
        ]

    names = [r[0] for r in results]
    passed = [r[1] for r in results]
    failed = [r[2] for r in results]
    tot_p, tot_f = sum(passed), sum(failed)

    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    yidx = range(len(names))
    ax.barh(yidx, passed, color=GREEN, label="pass", height=0.62,
            edgecolor=BG, linewidth=1.2)
    ax.barh(yidx, failed, left=passed, color=RED, label="fail", height=0.62)
    ax.set_yticks(list(yidx))
    ax.set_yticklabels(names, fontsize=9, color=INK)
    ax.invert_yaxis()
    ax.set_xlabel("assertions checked", color=MUTED)
    ax.set_title(f"Testbench Results — {tot_p} / {tot_p + tot_f} assertions passing",
                 fontsize=13.5, fontweight="bold", color=INK, pad=12)
    for i, (p, f_) in enumerate(zip(passed, failed)):
        ax.text(p + f_ + 0.06, i, f"{p}/{p + f_}", va="center", fontsize=8.2,
                color=GOLD, fontweight="bold")
    ax.set_xlim(0, max(passed) + 1.2)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color(GRID)
    ax.legend(loc="lower right", frameon=False, labelcolor=INK)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    save(fig, "test_results.png")


def main():
    print("Generating dark-themed figures into for_generating_readme/ ...")
    fig_formats()
    fig_instr_table()
    fig_timeline()
    fig_test_results()
    print("Done.")


if __name__ == "__main__":
    main()
