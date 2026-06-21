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
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

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
# 0. HERO — 2D datapath schematic of the processor (multi-cycle, P&H style)
# ---------------------------------------------------------------------------
def fig_hero():
    fig, ax = plt.subplots(figsize=(16, 8.6))
    ax.set_xlim(0, 200)
    ax.set_ylim(0, 108)
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # ---- drawing primitives -------------------------------------------------
    def unit(x, y, w, h, label, ec, fc=CARD, fs=10, sub=None, clk=False,
             tc=INK):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
            linewidth=1.8, edgecolor=ec, facecolor=fc, zorder=4))
        ax.text(x + w / 2, y + h / 2 + (1.6 if sub else 0), label,
                ha="center", va="center", fontsize=fs, color=tc,
                fontweight="bold", zorder=5)
        if sub:
            ax.text(x + w / 2, y + h / 2 - 2.4, sub, ha="center", va="center",
                    fontsize=7.4, color=MUTED, zorder=5)
        if clk:  # little clock notch, bottom-left
            ax.add_patch(Polygon([(x, y), (x + 2.6, y), (x, y + 2.6)],
                                 closed=True, facecolor=ec, edgecolor=ec,
                                 zorder=6))
        return (x, y, w, h)

    def mux(x, y, w, h, ec=PURPLE, label=None, flip=False):
        # vertical trapezoid; narrow side is the output. Default output is on
        # the right; flip=True puts the output on the left.
        if flip:
            pts = [(x + w, y), (x, y + h * 0.18), (x, y + h * 0.82), (x + w, y + h)]
        else:
            pts = [(x, y), (x + w, y + h * 0.18), (x + w, y + h * 0.82), (x, y + h)]
        ax.add_patch(Polygon(pts, closed=True, linewidth=1.6, edgecolor=ec,
                             facecolor=PANEL, zorder=4))
        if label:
            ax.text(x + w / 2, y + h / 2, label, ha="center",
                    va="center", fontsize=6.4, color=MUTED, rotation=90,
                    zorder=5)
        return (x, y, w, h)

    def alu(x, y, w, h, ec=GOLD):
        pts = [(x, y + h), (x, y + 0.60 * h), (x + 0.22 * w, y + 0.5 * h),
               (x, y + 0.40 * h), (x, y),
               (x + w, y + 0.30 * h), (x + w, y + 0.70 * h)]
        ax.add_patch(Polygon(pts, closed=True, linewidth=2.0, edgecolor=ec,
                             facecolor="#10243d", zorder=4))
        ax.text(x + w * 0.62, y + h * 0.5, "ALU", ha="center", va="center",
                fontsize=12, color=ec, fontweight="bold", zorder=5)
        return (x, y, w, h)

    def wire(pts, color=MUTED, lw=1.7, arrow=True, z=2, ls="-"):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, color=color, lw=lw, zorder=z, ls=ls,
                solid_capstyle="round")
        if arrow:
            ax.annotate("", xy=pts[-1], xytext=pts[-2],
                        arrowprops=dict(arrowstyle="-|>", color=color, lw=lw),
                        zorder=z + 1)

    def tag(x, y, text, color=MUTED, fs=7.2, ha="center", style="normal"):
        ax.text(x, y, text, ha=ha, va="center", fontsize=fs, color=color,
                zorder=7, style=style, fontweight="bold")

    # ---- title --------------------------------------------------------------
    ax.text(100, 104, "RV32I Multi-Cycle Processor — Datapath",
            ha="center", fontsize=19, fontweight="bold", color=INK)
    ax.text(100, 99.2,
            "single shared memory port  ·  11-state control FSM  ·  "
            "32 x 32-bit register file",
            ha="center", fontsize=9.5, color=MUTED, style="italic")

    # ---- Control FSM band (top) --------------------------------------------
    ax.add_patch(FancyBboxPatch((8, 95), 184, 7,
                 boxstyle="round,pad=0,rounding_size=1.5",
                 linewidth=2, edgecolor=RED, facecolor="#2a0f1c", zorder=3))
    ax.text(100, 98.5,
            "CONTROL  FSM      "
            "FETCH1 → FETCH2 → FETCH3 → DECODE → EXEC → "
            "{ WB | MEM1·2·3 | BRANCH | JUMP } → FETCH1",
            ha="center", va="center", fontsize=10, color="#FFE4E6",
            fontweight="bold", zorder=5)

    # =========================================================================
    #  DATAPATH  (left -> right);  exec_result is the single write-back source
    # =========================================================================
    # --- PC + address mux + unified memory ----------------------------------
    unit(4, 40, 12, 12, "PC", BLUE, sub="32-bit", clk=True)
    mux(20, 36, 5, 20, ec=PURPLE, label="addr")
    unit(29, 30, 18, 32, "Unified\nMemory", ORANGE, fc="#3B1D0B",
         sub="instr + data", tc="#FFEDD5")
    wire([(16, 48), (20, 52)], BLUE)                    # PC -> addr mux
    wire([(25, 46), (29, 46)], ORANGE, lw=2.2)          # addr mux -> memory
    tag(27, 48.4, "mem_addr", ORANGE, 6.4)

    # --- Instruction register + field breakout ------------------------------
    unit(54, 38, 13, 16, "Instr.\nRegister", BLUE, clk=True, sub="instr")
    wire([(47, 50), (54, 50)], GREEN, lw=2.2)           # mem_rdata -> IR
    tag(50.5, 52.2, "mem_rdata", GREEN, 6.4)
    ax.add_patch(FancyBboxPatch((52, 27), 17, 6,
                 boxstyle="round,pad=0,rounding_size=1",
                 linewidth=1.3, edgecolor=SLATE, facecolor=PANEL, zorder=3))
    ax.text(60.5, 30.6, "decode fields", ha="center", fontsize=6.4,
            color=MUTED, zorder=5)
    ax.text(60.5, 28.4, "opcode rd funct3 rs1 rs2 funct7", ha="center",
            fontsize=5.6, color=INK, zorder=5)
    wire([(60.5, 38), (60.5, 33)], SLATE, lw=1.2, arrow=False)

    # --- Register file + A/B operand registers ------------------------------
    unit(76, 32, 16, 28, "Register\nFile", BLUE, sub="32 x 32-bit", clk=True)
    wire([(69, 51), (76, 53)], INK); tag(72.5, 54.6, "rs1", MUTED, 6.0)
    wire([(69, 45), (76, 40)], INK); tag(72.5, 41.4, "rs2", MUTED, 6.0)
    unit(95, 50, 7, 8, "A", BLUE, sub="rs1_val", clk=True, fs=9)
    unit(95, 34, 7, 8, "B", BLUE, sub="rs2_val", clk=True, fs=9)
    wire([(92, 54), (95, 54)], INK)
    wire([(92, 38), (95, 38)], INK)

    # --- Immediate generator -------------------------------------------------
    unit(76, 14, 16, 12, "Immediate\nGenerator", PURPLE, sub="I  S  B  U  J",
         tc="#E0E7FF")
    wire([(60.5, 27), (60.5, 20), (76, 20)], PURPLE, lw=1.4)   # fields -> imm

    # --- ALU operand muxes + ALU --------------------------------------------
    mux(106, 49, 4.5, 10, ec=PURPLE)                    # A-side
    mux(106, 31, 4.5, 16, ec=PURPLE, label="rs2/imm")   # B-side
    alu(115, 32, 17, 27)
    wire([(102, 54), (106, 54)], INK)                   # A reg -> A mux
    wire([(102, 38), (106, 40)], INK)                   # B reg -> B mux
    wire([(92, 20), (104, 20), (104, 35), (106, 35)], PURPLE, lw=1.4)  # imm->Bmux
    wire([(110.5, 54), (115, 52)], INK)                 # A mux -> ALU
    wire([(110.5, 39), (115, 40)], INK)                 # B mux -> ALU

    # --- Result-source mux -> exec_result register (the write-back source) --
    mux(137, 36, 5, 23, ec=GREEN, label="result src")
    unit(146, 43, 11, 11, "exec_\nresult", GOLD, fc="#1c1606", clk=True,
         tc=GOLD, fs=8.5)
    wire([(132, 45.5), (137, 47)], INK, lw=1.8)         # ALU result -> mux
    wire([(140, 15), (140, 41), (137, 41)], ORANGE, lw=1.6)  # load_data -> mux
    wire([(139.5, 33), (139.5, 36)], BLUE, lw=1.3)      # PC+4 / LUI / AUIPC
    tag(139.5, 31.4, "PC+4 · imm_u · PC+imm_u", BLUE, 5.6)
    wire([(142, 47.5), (146, 48.5)], GOLD, lw=2.0)      # mux -> exec_result

    # --- Branch comparator ---------------------------------------------------
    unit(106, 17, 18, 9, "Branch  Compare", PURPLE, sub="taken?",
         tc="#E0F2FE", fs=9)
    wire([(98.5, 50), (101, 50), (101, 24), (106, 24)], SLATE, lw=1.2)  # A->cmp
    wire([(99.5, 42), (99.5, 21), (106, 21)], SLATE, lw=1.2)            # B->cmp

    # --- Load / Store align + mask ------------------------------------------
    unit(115, 5, 50, 10, "Load / Store   Align + Mask", ORANGE, fc="#3B1D0B",
         sub="LB LH LW LBU LHU   ·   SB SH SW", tc="#FFEDD5", fs=10)
    wire([(129, 32), (129, 15)], GOLD, lw=1.6)          # ALU addr -> LSU
    tag(133.5, 28, "mem_address", GOLD, 6.0, ha="left")
    # shared memory bus rails (LSU <-> memory)
    wire([(115, 11), (38, 11), (38, 30)], ORANGE, lw=2.2)   # wdata/wmask -> mem
    wire([(34, 30), (34, 8), (115, 8)], GREEN, lw=2.0)      # rdata (load) -> LSU
    tag(74, 12.6, "mem_wdata  ·  mem_wmask[3:0]", ORANGE, 6.4)
    tag(74, 6.4, "mem_rdata  (load data)", GREEN, 6.4)

    # --- write-back: exec_result wraps back to the register-file write port --
    wire([(157, 48.5), (162, 48.5), (162, 84), (84, 84), (84, 60)],
         GREEN, lw=2.0)
    tag(120, 86, "write-back   →   regfile[rd]   (rd ≠ x0)", GREEN, 7.4)

    # --- next-PC logic (adders + next-PC mux, output feeds PC) --------------
    mux(172, 35, 5, 24, ec=GOLD, label="next PC", flip=True)
    unit(182, 53, 16, 6, "PC + 4", SLATE, fs=8.4)
    unit(182, 45, 16, 6, "PC + imm_b", BLUE, fs=7.8, sub="branch")
    unit(182, 37, 16, 6, "PC + imm_j", PURPLE, fs=7.8, sub="JAL")
    unit(182, 28, 16, 6, "(rs1+imm_i)&~1", ORANGE, fs=7.0, sub="JALR")
    for yy in [56, 48, 40, 31]:
        wire([(182, yy), (177, yy if yy > 34 else 37)], MUTED, lw=1.2,
             arrow=False)
    wire([(172, 47), (167, 47), (167, 90), (10, 90), (10, 52)],
         GOLD, lw=2.0)                                  # next PC -> PC
    tag(88, 92, "next PC", GOLD, 7.4)
    wire([(124, 21), (175, 21), (175, 35)], PURPLE, lw=1.3, ls="--")  # select
    tag(150, 19, "branch_taken · target select", PURPLE, 6.0)

    # ---- control lines (dashed, FSM band -> the muxes it sequences) --------
    for cx, top in [(22, 56), (108, 47), (139.5, 59), (174.5, 59)]:
        wire([(cx, 95), (cx, top)], RED, lw=1.0, ls=":", arrow=False, z=1)

    # ---- legend -------------------------------------------------------------
    items = [("register", BLUE), ("memory / align", ORANGE),
             ("immediate / mux", PURPLE), ("ALU / result", GOLD),
             ("write-back", GREEN), ("control", RED)]
    lx = 8
    for lbl, c in items:
        ax.add_patch(Rectangle((lx, 1.0), 2.2, 2.2, facecolor=c,
                               edgecolor=c, zorder=5))
        ax.text(lx + 3.0, 2.1, lbl, fontsize=7.4, color=INK, va="center")
        lx += len(lbl) * 1.5 + 11

    save(fig, "processor_datapath_hero.png")


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
    fig_hero()
    fig_formats()
    fig_instr_table()
    fig_timeline()
    fig_test_results()
    print("Done.")


if __name__ == "__main__":
    main()
