# RV32I Multi-Cycle Processor (Verilog)

```mermaid
%%{init: {
  "theme": "base",
  "themeVariables": {
    "background": "#070A12",
    "primaryColor": "#111827",
    "primaryTextColor": "#E6EAF7",
    "primaryBorderColor": "#334155",
    "lineColor": "#8aa0c6",
    "fontFamily": "Inter, Segoe UI, Arial, sans-serif",
    "fontSize": "15px",
    "clusterBkg": "#0b1220",
    "clusterBorder": "#243149"
  },
  "flowchart": { "curve": "basis", "nodeSpacing": 40, "rankSpacing": 60, "htmlLabels": true, "padding": 10 }
}}%%
flowchart LR
    PC(["PC"]):::pc

    subgraph FE["①  FETCH&nbsp;&nbsp;"]
        direction TB
        MEM[("Unified<br/>Memory")]:::mem
        IR["Instruction<br/>Register"]:::reg
    end

    subgraph DE["②  DECODE&nbsp;&nbsp;"]
        direction TB
        DEC["Decoder<br/><small>opcode · funct3 · funct7</small>"]:::dec
        RF["Register File<br/><small>32 × 32-bit</small>"]:::reg
        IMM["Immediate Gen<br/><small>I S B U J</small>"]:::imm
    end

    subgraph EX["③  EXECUTE&nbsp;&nbsp;"]
        direction TB
        ALU{{"ALU<br/><small>add sub sll slt<br/>xor srl sra or and</small>"}}:::alu
        CMP{"Branch<br/>Compare"}:::cmp
    end

    subgraph MM["④  MEMORY&nbsp;&nbsp;"]
        direction TB
        LSU["Load / Store<br/><small>align + mask</small>"]:::mem
    end

    subgraph WB["⑤  WRITE-BACK&nbsp;&nbsp;"]
        direction TB
        EXEC(["exec_result"]):::wb
    end

    FSM["⚙ CONTROL FSM<br/><small>FETCH1·2·3 → DECODE → EXEC →<br/>WB / MEM / BRANCH / JUMP</small>"]:::ctrl

    PC ==> MEM
    MEM == "mem_rdata" ==> IR
    IR --> DEC
    DEC -- "rs1 · rs2" --> RF
    DEC --> IMM
    RF -- "rs1_val" --> ALU
    IMM -- "imm" --> ALU
    RF --> CMP
    ALU == "mem_address" ==> LSU
    ALU -- "result" --> EXEC
    LSU -- "load data" --> EXEC
    EXEC == "regfile[rd]" ==> RF
    CMP -. "taken" .-> PC
    EXEC -. "next PC" .-> PC
    FSM -. "sequences" .-> EX
    FSM -. " " .-> MM

    classDef pc   fill:#0B1020,stroke:#FFD34D,stroke-width:2.5px,color:#FDE68A;
    classDef reg  fill:#101c30,stroke:#60A5FA,stroke-width:2px,color:#DCE6FF;
    classDef imm  fill:#191634,stroke:#8B93F8,stroke-width:2px,color:#E2E0FF;
    classDef dec  fill:#1b1740,stroke:#A5B4FC,stroke-width:2px,color:#E6E9FF;
    classDef alu  fill:#13243d,stroke:#FACC15,stroke-width:3px,color:#FDE68A;
    classDef cmp  fill:#1b1740,stroke:#A5B4FC,stroke-width:2px,color:#E6E9FF;
    classDef mem  fill:#2a1408,stroke:#F97316,stroke-width:2.5px,color:#FFE3C7;
    classDef wb   fill:#0f2a1e,stroke:#6EE7B7,stroke-width:3px,color:#CFFCE6;
    classDef ctrl fill:#2a0f1c,stroke:#F43F5E,stroke-width:3px,color:#FFD9E0;

    linkStyle default stroke-width:2px;
```

<p align="center"><sub><b>The RV32I multi-cycle datapath.</b> A value flows left → right through five stages; the control FSM sequences every step, and <code>exec_result</code> is the single write-back source. Faithful to <a href="rtl/riscv_processor.sv"><code>rtl/riscv_processor.sv</code></a>.</sub></p>

## This is not the Project Report; for the full design write-up, see [project_report.md](<project_report.md>).

A from-scratch **RISC-V RV32I** processor written in Verilog/SystemVerilog for
the *DAC-102 Verilog Project*. It implements the complete RV32I base integer
instruction set (all 37 instructions) except `ecall`/`ebreak`, and exposes the
mandated memory interface so it can be driven by an automated testbench.

The synthesizable core is [rtl/riscv_processor.sv](rtl/riscv_processor.sv). A
self-checking testbench in [tb/testbench.sv](tb/testbench.sv) assembles small
RV32I programs, runs them, and checks the architectural results — **38 / 38
assertions pass**.

For the detailed micro-architecture, datapath/FSM diagrams, and verification
discussion, read [project_report.md](<project_report.md>).

## Repository Layout

```text
.
├── rtl/
│   └── riscv_processor.sv          # The RV32I CPU — top module / deliverable
├── tb/
│   └── testbench.sv                # Self-checking testbench (16 groups / 38 assertions)
├── sim/
│   ├── run.sh                      # One-command build + run (iverilog + vvp)
│   └── sim.log                     # Committed simulation transcript (38/38 pass)
├── for_generating_readme/          # Figure tooling + generated assets
│   ├── generate_figures.py         # matplotlib plots (dark theme)
│   └── *.png                       # formats, instr table, timeline, results
├── docs/
│   └── assignment_spec.pdf         # Original assignment specification
├── project_report.md               # Full project report and design logic
└── README.md
```

## Requirements

* [Icarus Verilog](https://steveicarus.github.io/iverilog/) 11+ (`iverilog`, `vvp`)
  — recommended by the assignment.
* Optional, to regenerate the report figures: Python 3.10+ with `matplotlib`.

Install on macOS / Linux:

```bash
# macOS
brew install icarus-verilog

# Debian / Ubuntu
sudo apt-get install iverilog

# optional figure dependencies
python -m pip install matplotlib
```

## Run The Testbench

From the repository root:

```bash
iverilog -g2012 -o sim/rv_sim rtl/riscv_processor.sv tb/testbench.sv
vvp sim/rv_sim
```

Or use the convenience script:

```bash
bash sim/run.sh
```

Either way you should see:

```text
============================================================
TEST SUMMARY: 38 PASSED, 0 FAILED out of 38 total
ALL TESTS PASSED!
============================================================
```

The committed transcript is at [sim/sim.log](sim/sim.log).

## Submission File

The assignment requires the top module to be named `<roll_number>_riscv.v`. That
file is committed at the repository root as
[25323045_riscv.v](25323045_riscv.v) — identical logic to
[rtl/riscv_processor.sv](rtl/riscv_processor.sv), with the module declared as an
escaped Verilog identifier (a module name starting with a digit must be written
`\25323045_riscv`). It passes the same 38/38 testbench:

```bash
iverilog -g2012 -o sim/rv_sim 25323045_riscv.v tb/testbench.sv  # see note below
```

> The bundled testbench instantiates `riscv_processor`; the automated grader
> instantiates `\25323045_riscv`. Both forms are verified equivalent.

## Optional: Regenerate Figures

All figures in `for_generating_readme/` are already committed. The dark-themed
plots (instruction formats, instruction table, execution timeline, test
results) are produced by matplotlib:

```bash
python for_generating_readme/generate_figures.py   # after a fresh sim/sim.log
```

The **hero datapath** and the **control-FSM** diagram are authored as
[Mermaid](https://mermaid.js.org) blocks directly in this README and in
[project_report.md](<project_report.md>), so they render on GitHub with no build
step.

## Method Summary

The core is a **multi-cycle** design driven by a single 11-state FSM:

```text
FETCH1 -> FETCH2 -> FETCH3 -> DECODE -> EXEC -> { WB | MEM1..3 | BRANCH | JUMP } -> FETCH1
```

`EXEC` dispatches by opcode: arithmetic / `LUI` / `AUIPC` go straight to
write-back; loads and stores walk the three-state memory sequence; branches and
jumps redirect the PC. The three-cycle fetch models the one-cycle latency of
the memory bus (assert strobe → settle → capture), and the same pattern is
reused for loads. Sub-word loads and stores are aligned and sign/zero-extended
from the two low address bits, and `x0` is hardwired to zero.

Full details — including the ALU, immediate generation, branch logic, memory
interface, and the complete verification matrix — are in
[project_report.md](<project_report.md>).

## Latency

Being a multi-cycle design, the processor spends a fixed, instruction-dependent
number of clock cycles per instruction rather than retiring one per cycle. Every
instruction pays a common 5-cycle front end — a three-cycle fetch (`FETCH1→2→3`,
which models the one-cycle latency of the mandated memory bus), `DECODE`, and
`EXEC` — and then takes a different terminal path. Arithmetic/logical
instructions, `LUI`, `AUIPC`, branches, and jumps finish in **6 cycles**; stores
walk the three-state memory sequence for **8 cycles**; loads add a write-back and
take **9 cycles**. There is no pipeline, so these cycle counts are also the CPI:
effective performance ranges from CPI ≈ 6 on branch/ALU-heavy code to CPI ≈ 9 on
load-bound code, and the wall-clock latency of any instruction is simply its
cycle count times the clock period (e.g. at a 100 MHz / 10 ns clock, a load
completes in ~90 ns and an ALU op in ~60 ns). Because every terminal state
returns unconditionally to `FETCH1`, latency is fully deterministic — there are
no stalls, variable-latency hazards, or misprediction penalties. The most
direct way to cut it would be to collapse the three-cycle fetch (combinational
instruction memory) or to pipeline the datapath; both are discussed in
[project_report.md](<project_report.md>).

## Runtime Analysis

The total time a program takes is the sum of its per-instruction cycle counts
multiplied by the clock period; with no pipeline and no variable-latency
hazards, this is exact rather than statistical. The testbench clocks the core at
`always #5 clk = ~clk`, i.e. a 10 ns period (**100 MHz**), so an ALU/branch/jump
instruction takes 60 ns, a store 80 ns, and a load 90 ns. As a worked example,
the *sum 1..5* loop program in Test 15 executes 19 dynamic instructions — three
`addi` to initialise, then five iterations of `add`/`addi`/`blt` (15
instructions), and a final `sw` to store the result. That is 18 six-cycle
instructions plus one eight-cycle store, i.e. **116 clock cycles ≈ 1.16 µs** of
core execution, and the program produces the correct answer (`0x0f`). End to
end, the full self-checking testbench — all 16 programs, plus the five-cycle
reset that precedes each one and the `wait_store` polling between checks — runs
to completion in **9.195 µs of simulated time** (`$finish` at 9,195,000 ps),
which is the figure reported in [sim/sim.log](sim/sim.log). The runtime is
therefore data-independent in the sense that two programs with the same dynamic
instruction mix always take the same number of cycles; the only knob that moves
the wall-clock number is the dynamic instruction count (loop trip counts,
branch outcomes) and the target clock frequency. Driving the same core at a
higher `Fmax` scales every figure above down linearly without changing the
cycle counts — and the next section establishes that real frequency by
synthesis rather than by assumption.

## Synthesis &amp; Maximum Clock Frequency

The 100 MHz above is only the testbench's clock; the design's *real* speed
limit is set by its longest combinational path. To measure it, the core was
synthesised with [Yosys](https://yosyshq.net/yosys/) 0.66 and technology-mapped
(ABC) onto the **Nangate45 Open Cell Library** (a real 45 nm-class standard-cell
liberty, typical corner). Static timing on the mapped netlist reports:

| Metric | Value |
| --- | --- |
| Critical-path delay | **1.75 ns** (1747 ps) |
| **Maximum clock frequency** | **≈ 572 MHz** (1 / 1.75 ns) |
| Critical path | `instr[1]` (opcode) → 31 levels of decode/ALU select logic → registered result mux |
| Mapped area | ≈ 13,808 µm² (8568 cells, of which 1273 flip-flops) |

The critical path runs from an opcode bit of the instruction register through
the combinational decode and ALU/operand-select cone into the registered
`exec_result`/next-state mux — i.e. the `EXEC` stage, as expected for a design
whose datapath is otherwise shallow. **Important caveat:** this is a
synthesis-/technology-mapping estimate with `WireLoad = none`, so it counts gate
delays only — it excludes routing parasitics, clock skew/uncertainty, and setup
margin. A realistic post-place-and-route target on the same process would be
lower (typically 20–40 %), so the honest headline is *“synthesises to a 1.75 ns
gate-level critical path, ≈ 570 MHz pre-layout on Nangate45.”*

At this synthesised speed the cycle counts above translate to ≈ 10.5 ns per
ALU/branch/jump, ≈ 14 ns per store, ≈ 15.7 ns per load, and the *sum 1..5* loop
(116 cycles) completes in ≈ 203 ns. To reproduce:

```bash
yosys -p '
  read_verilog -sv rtl/riscv_processor.sv
  synth -top riscv_processor -flatten
  dfflibmap -liberty nangate45.lib
  abc -liberty nangate45.lib -script +strash;&get,-n;&dch,-f;&nf;&put;topo;stime'
```
