`timescale 1ns / 1ps

module testbench;

    reg clk;
    reg reset;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata;
    wire [3:0] mem_wmask;
    wire [31:0] mem_rdata;
    wire mem_rstrb;
    reg mem_rbusy;
    reg mem_wbusy;

    reg [31:0] memory [0:4095];
    reg [31:0] read_data;

    always @(posedge clk) begin
        if (mem_rstrb) begin
            read_data <= memory[mem_addr >> 2];
        end
    end

    assign mem_rdata = read_data;

    always @(posedge clk) begin
        if (mem_wmask[0]) memory[mem_addr >> 2][7:0] <= mem_wdata[7:0];
        if (mem_wmask[1]) memory[mem_addr >> 2][15:8] <= mem_wdata[15:8];
        if (mem_wmask[2]) memory[mem_addr >> 2][23:16] <= mem_wdata[23:16];
        if (mem_wmask[3]) memory[mem_addr >> 2][31:24] <= mem_wdata[31:24];
    end

    initial begin
        mem_rbusy = 1'b0;
        mem_wbusy = 1'b0;
    end

    initial clk = 0;
    always #5 clk = ~clk;

    riscv_processor dut (
        .clk (clk),
        .mem_addr (mem_addr),
        .mem_wdata (mem_wdata),
        .mem_wmask (mem_wmask),
        .mem_rdata (mem_rdata),
        .mem_rstrb (mem_rstrb),
        .mem_rbusy (mem_rbusy),
        .mem_wbusy (mem_wbusy),
        .reset (reset)
    );

    integer total_pass = 0;
    integer total_fail = 0;
    integer test_num = 0;

    task init_memory;
        integer j;
        begin
            for (j = 0; j < 4096; j = j + 1)
                memory[j] = 32'd0;
            read_data = 32'd0;
        end
    endtask

    task reset_cpu;
        begin
            reset = 1'b0;
            repeat (5) @(posedge clk);
            reset = 1'b1;
        end
    endtask

    task wait_store;
        begin
            @(posedge clk);
            while (mem_wmask == 4'b0000) begin
                @(posedge clk);
            end

            @(posedge clk);
        end
    endtask

    task check(input [31:0] addr, input [31:0] expected);
        begin
            if (memory[addr >> 2] === expected) begin
                $display("  [PASS] memory[0x%04h] = 0x%08h (expected 0x%08h)", addr, memory[addr >> 2], expected);
                total_pass = total_pass + 1;
            end else begin
                $display("  [FAIL] memory[0x%04h] = 0x%08h (expected 0x%08h)", addr, memory[addr >> 2], expected);
                total_fail = total_fail + 1;
            end
        end
    endtask

    function [31:0] rv_rtype;
        input [6:0] funct7;
        input [4:0] rs2, rs1;
        input [2:0] funct3;
        input [4:0] rd;
        input [6:0] opcode;
        rv_rtype = {funct7, rs2, rs1, funct3, rd, opcode};
    endfunction

    function [31:0] rv_itype;
        input [11:0] imm;
        input [4:0] rs1;
        input [2:0] funct3;
        input [4:0] rd;
        input [6:0] opcode;
        rv_itype = {imm, rs1, funct3, rd, opcode};
    endfunction

    function [31:0] rv_stype;
        input [11:0] imm;
        input [4:0] rs2, rs1;
        input [2:0] funct3;
        input [6:0] opcode;
        rv_stype = {imm[11:5], rs2, rs1, funct3, imm[4:0], opcode};
    endfunction

    function [31:0] rv_btype;
        input [12:0] imm;
        input [4:0] rs2, rs1;
        input [2:0] funct3;
        input [6:0] opcode;
        rv_btype = {imm[12], imm[10:5], rs2, rs1, funct3, imm[4:1], imm[11], opcode};
    endfunction

    function [31:0] rv_utype;
        input [19:0] imm;
        input [4:0] rd;
        input [6:0] opcode;
        rv_utype = {imm, rd, opcode};
    endfunction

    function [31:0] rv_jtype;
        input [20:0] imm;
        input [4:0] rd;
        input [6:0] opcode;
        rv_jtype = {imm[20], imm[10:1], imm[11], imm[19:12], rd, opcode};
    endfunction

    localparam [6:0] OP_R = 7'b0110011;
    localparam [6:0] OP_I = 7'b0010011;
    localparam [6:0] OP_L = 7'b0000011;
    localparam [6:0] OP_S = 7'b0100011;
    localparam [6:0] OP_B = 7'b1100011;
    localparam [6:0] OP_JAL= 7'b1101111;
    localparam [6:0] OP_JALR = 7'b1100111;
    localparam [6:0] OP_LUI = 7'b0110111;
    localparam [6:0] OP_AUIPC= 7'b0010111;

    initial begin
        $display("============================================================");
        $display("RV32I Multi-Cycle Processor Testbench");
        $display("============================================================");

        test_num = 1;
        $display("\nTest %0d: ADD / SUB", test_num);
        init_memory;

        memory[0] = rv_itype(12'd15, 5'd0, 3'b000, 5'd1, OP_I);

        memory[1] = rv_itype(12'd7, 5'd0, 3'b000, 5'd2, OP_I);

        memory[2] = rv_rtype(7'b0000000, 5'd2, 5'd1, 3'b000, 5'd3, OP_R);

        memory[3] = rv_rtype(7'b0100000, 5'd2, 5'd1, 3'b000, 5'd4, OP_R);

        memory[4] = rv_stype(12'h100, 5'd3, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store;
        check(32'h100, 32'd22);

        init_memory;
        memory[0] = rv_itype(12'd15, 5'd0, 3'b000, 5'd1, OP_I);
        memory[1] = rv_itype(12'd7, 5'd0, 3'b000, 5'd2, OP_I);
        memory[2] = rv_rtype(7'b0000000, 5'd2, 5'd1, 3'b000, 5'd3, OP_R);
        memory[3] = rv_rtype(7'b0100000, 5'd2, 5'd1, 3'b000, 5'd4, OP_R);
        memory[4] = rv_stype(12'h100, 5'd3, 5'd0, 3'b010, OP_S);
        memory[5] = rv_stype(12'h104, 5'd4, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store;
        check(32'h100, 32'd22);
        wait_store;
        check(32'h104, 32'd8);

        test_num = 2;
        $display("\nTest %0d: AND / OR / XOR", test_num);
        init_memory;
        memory[0] = rv_itype(12'hFF, 5'd0, 3'b000, 5'd1, OP_I);
        memory[1] = rv_itype(12'h0F, 5'd0, 3'b000, 5'd2, OP_I);
        memory[2] = rv_rtype(7'b0000000, 5'd2, 5'd1, 3'b111, 5'd3, OP_R);
        memory[3] = rv_rtype(7'b0000000, 5'd2, 5'd1, 3'b110, 5'd4, OP_R);
        memory[4] = rv_rtype(7'b0000000, 5'd2, 5'd1, 3'b100, 5'd5, OP_R);
        memory[5] = rv_stype(12'h100, 5'd3, 5'd0, 3'b010, OP_S);
        memory[6] = rv_stype(12'h104, 5'd4, 5'd0, 3'b010, OP_S);
        memory[7] = rv_stype(12'h108, 5'd5, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store; check(32'h100, 32'h0F);
        wait_store; check(32'h104, 32'hFF);
        wait_store; check(32'h108, 32'hF0);

        test_num = 3;
        $display("\nTest %0d: SLT / SLTU", test_num);
        init_memory;
        memory[0] = rv_itype(-12'sd5 & 12'hFFF, 5'd0, 3'b000, 5'd1, OP_I);
        memory[1] = rv_itype(12'd10, 5'd0, 3'b000, 5'd2, OP_I);
        memory[2] = rv_rtype(7'b0000000, 5'd2, 5'd1, 3'b010, 5'd3, OP_R);
        memory[3] = rv_rtype(7'b0000000, 5'd2, 5'd1, 3'b011, 5'd4, OP_R);
        memory[4] = rv_rtype(7'b0000000, 5'd1, 5'd2, 3'b010, 5'd5, OP_R);
        memory[5] = rv_stype(12'h100, 5'd3, 5'd0, 3'b010, OP_S);
        memory[6] = rv_stype(12'h104, 5'd4, 5'd0, 3'b010, OP_S);
        memory[7] = rv_stype(12'h108, 5'd5, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store; check(32'h100, 32'd1);
        wait_store; check(32'h104, 32'd0);
        wait_store; check(32'h108, 32'd0);

        test_num = 4;
        $display("\nTest %0d: ADDI / ANDI / ORI / XORI", test_num);
        init_memory;
        memory[0] = rv_itype(12'd100, 5'd0, 3'b000, 5'd1, OP_I);
        memory[1] = rv_itype(12'h0F0, 5'd1, 3'b111, 5'd2, OP_I);
        memory[2] = rv_itype(12'h00F, 5'd1, 3'b110, 5'd3, OP_I);
        memory[3] = rv_itype(12'hFFF, 5'd1, 3'b100, 5'd4, OP_I);
        memory[4] = rv_stype(12'h100, 5'd1, 5'd0, 3'b010, OP_S);
        memory[5] = rv_stype(12'h104, 5'd2, 5'd0, 3'b010, OP_S);
        memory[6] = rv_stype(12'h108, 5'd3, 5'd0, 3'b010, OP_S);
        memory[7] = rv_stype(12'h10C, 5'd4, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store; check(32'h100, 32'd100);
        wait_store; check(32'h104, 32'h60);
        wait_store; check(32'h108, 32'h6F);
        wait_store; check(32'h10C, 32'hFFFFFF9B);

        test_num = 5;
        $display("\nTest %0d: SLL / SRL / SRA", test_num);
        init_memory;
        memory[0] = rv_itype(12'd1, 5'd0, 3'b000, 5'd1, OP_I);
        memory[1] = rv_itype(12'd4, 5'd0, 3'b000, 5'd2, OP_I);
        memory[2] = rv_rtype(7'b0000000, 5'd2, 5'd1, 3'b001, 5'd3, OP_R);

        memory[3] = rv_itype(-12'sd16 & 12'hFFF, 5'd0, 3'b000, 5'd5, OP_I);
        memory[4] = rv_rtype(7'b0000000, 5'd2, 5'd5, 3'b101, 5'd6, OP_R);
        memory[5] = rv_rtype(7'b0100000, 5'd2, 5'd5, 3'b101, 5'd7, OP_R);
        memory[6] = rv_stype(12'h100, 5'd3, 5'd0, 3'b010, OP_S);
        memory[7] = rv_stype(12'h104, 5'd6, 5'd0, 3'b010, OP_S);
        memory[8] = rv_stype(12'h108, 5'd7, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store; check(32'h100, 32'd16);
        wait_store; check(32'h104, 32'h0FFFFFFF);
        wait_store; check(32'h108, 32'hFFFFFFFF);

        test_num = 6;
        $display("\nTest %0d: SLLI / SRLI / SRAI", test_num);
        init_memory;
        memory[0] = rv_itype(12'd1, 5'd0, 3'b000, 5'd1, OP_I);
        memory[1] = rv_itype(12'b000000_000100, 5'd1, 3'b001, 5'd2, OP_I);

        memory[2] = rv_itype(-12'sd16 & 12'hFFF, 5'd0, 3'b000, 5'd5, OP_I);
        memory[3] = rv_itype(12'b000000_000100, 5'd5, 3'b101, 5'd6, OP_I);
        memory[4] = rv_itype(12'b010000_000100, 5'd5, 3'b101, 5'd7, OP_I);
        memory[5] = rv_stype(12'h100, 5'd2, 5'd0, 3'b010, OP_S);
        memory[6] = rv_stype(12'h104, 5'd6, 5'd0, 3'b010, OP_S);
        memory[7] = rv_stype(12'h108, 5'd7, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store; check(32'h100, 32'd16);
        wait_store; check(32'h104, 32'h0FFFFFFF);
        wait_store; check(32'h108, 32'hFFFFFFFF);

        test_num = 7;
        $display("\nTest %0d: LW / SW", test_num);
        init_memory;
        memory[128] = 32'hDEADBEEF;

        memory[0] = rv_itype(12'h200, 5'd0, 3'b000, 5'd1, OP_I);

        memory[1] = rv_itype(12'd0, 5'd1, 3'b010, 5'd2, OP_L);

        memory[2] = rv_stype(12'h100, 5'd2, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store;
        check(32'h100, 32'hDEADBEEF);

        test_num = 8;
        $display("\nTest %0d: LB / SB", test_num);
        init_memory;
        memory[128] = 32'hF1E2D3C4;

        memory[0] = rv_itype(12'h200, 5'd0, 3'b000, 5'd1, OP_I);

        memory[1] = rv_itype(12'd0, 5'd1, 3'b000, 5'd2, OP_L);

        memory[2] = rv_itype(12'd1, 5'd1, 3'b000, 5'd3, OP_L);

        memory[3] = rv_stype(12'h100, 5'd2, 5'd0, 3'b000, OP_S);

        memory[4] = rv_stype(12'h101, 5'd3, 5'd0, 3'b000, OP_S);
        reset_cpu;
        wait_store;
        check(32'h100, 32'h000000C4);
        wait_store;
        check(32'h100, 32'h0000D3C4);

        test_num = 9;
        $display("\nTest %0d: LH / SH", test_num);
        init_memory;
        memory[128] = 32'h87654321;

        memory[0] = rv_itype(12'h200, 5'd0, 3'b000, 5'd1, OP_I);

        memory[1] = rv_itype(12'd0, 5'd1, 3'b001, 5'd2, OP_L);

        memory[2] = rv_itype(12'd2, 5'd1, 3'b001, 5'd3, OP_L);

        memory[3] = rv_stype(12'h100, 5'd2, 5'd0, 3'b001, OP_S);

        memory[4] = rv_stype(12'h104, 5'd3, 5'd0, 3'b001, OP_S);
        reset_cpu;
        wait_store;
        check(32'h100, 32'h00004321);
        wait_store;
        check(32'h104, 32'h00008765);

        test_num = 10;
        $display("\nTest %0d: BEQ BNE BLT BGE BLTU BGEU", test_num);
        init_memory;

        memory[0] = rv_itype(12'd5, 5'd0, 3'b000, 5'd1, OP_I);

        memory[1] = rv_itype(12'd5, 5'd0, 3'b000, 5'd2, OP_I);

        memory[2] = rv_itype(12'd3, 5'd0, 3'b000, 5'd3, OP_I);

        memory[3] = rv_btype(13'd8, 5'd2, 5'd1, 3'b000, OP_B);

        memory[4] = rv_itype(12'd0, 5'd0, 3'b000, 5'd10, OP_I);

        memory[5] = rv_itype(12'd1, 5'd0, 3'b000, 5'd10, OP_I);

        memory[6] = rv_btype(13'd8, 5'd3, 5'd1, 3'b001, OP_B);

        memory[7] = rv_itype(12'd0, 5'd0, 3'b000, 5'd11, OP_I);

        memory[8] = rv_itype(12'd1, 5'd0, 3'b000, 5'd11, OP_I);

        memory[9] = rv_btype(13'd8, 5'd1, 5'd3, 3'b100, OP_B);

        memory[10] = rv_itype(12'd0, 5'd0, 3'b000, 5'd12, OP_I);

        memory[11] = rv_itype(12'd1, 5'd0, 3'b000, 5'd12, OP_I);

        memory[12] = rv_btype(13'd8, 5'd3, 5'd1, 3'b101, OP_B);

        memory[13] = rv_itype(12'd0, 5'd0, 3'b000, 5'd13, OP_I);

        memory[14] = rv_itype(12'd1, 5'd0, 3'b000, 5'd13, OP_I);

        memory[15] = rv_stype(12'h100, 5'd10, 5'd0, 3'b010, OP_S);

        memory[16] = rv_stype(12'h104, 5'd11, 5'd0, 3'b010, OP_S);

        memory[17] = rv_stype(12'h108, 5'd12, 5'd0, 3'b010, OP_S);

        memory[18] = rv_stype(12'h10C, 5'd13, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store; check(32'h100, 32'd1);
        wait_store; check(32'h104, 32'd1);
        wait_store; check(32'h108, 32'd1);
        wait_store; check(32'h10C, 32'd1);

        test_num = 11;
        $display("\nTest %0d: JAL", test_num);
        init_memory;

        memory[0] = rv_jtype(21'd8, 5'd1, OP_JAL);

        memory[1] = rv_itype(12'd0, 5'd0, 3'b000, 5'd10, OP_I);

        memory[2] = rv_itype(12'd1, 5'd0, 3'b000, 5'd10, OP_I);

        memory[3] = rv_stype(12'h100, 5'd1, 5'd0, 3'b010, OP_S);

        memory[4] = rv_stype(12'h104, 5'd10, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store; check(32'h100, 32'h04);
        wait_store; check(32'h104, 32'd1);

        test_num = 12;
        $display("\nTest %0d: JALR", test_num);
        init_memory;

        memory[0] = rv_itype(12'h10, 5'd0, 3'b000, 5'd1, OP_I);

        memory[1] = rv_itype(12'd0, 5'd1, 3'b000, 5'd2, OP_JALR);

        memory[2] = rv_itype(12'd0, 5'd0, 3'b000, 5'd10, OP_I);

        memory[3] = rv_itype(12'd0, 5'd0, 3'b000, 5'd10, OP_I);

        memory[4] = rv_itype(12'd1, 5'd0, 3'b000, 5'd10, OP_I);

        memory[5] = rv_stype(12'h100, 5'd2, 5'd0, 3'b010, OP_S);

        memory[6] = rv_stype(12'h104, 5'd10, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store; check(32'h100, 32'h08);
        wait_store; check(32'h104, 32'd1);

        test_num = 13;
        $display("\nTest %0d: LUI", test_num);
        init_memory;

        memory[0] = rv_utype(20'hDEADB, 5'd1, OP_LUI);

        memory[1] = rv_stype(12'h100, 5'd1, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store;
        check(32'h100, 32'hDEADB000);

        test_num = 14;
        $display("\nTest %0d: AUIPC", test_num);
        init_memory;

        memory[0] = rv_utype(20'h00001, 5'd1, OP_AUIPC);

        memory[1] = rv_stype(12'h100, 5'd1, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store;
        check(32'h100, 32'h1000);

        test_num = 15;
        $display("\nTest %0d: Loop program (sum 1..5)", test_num);
        init_memory;

        memory[0] = rv_itype(12'd0, 5'd0, 3'b000, 5'd1, OP_I);

        memory[1] = rv_itype(12'd1, 5'd0, 3'b000, 5'd2, OP_I);

        memory[2] = rv_itype(12'd6, 5'd0, 3'b000, 5'd3, OP_I);

        memory[3] = rv_rtype(7'b0000000, 5'd2, 5'd1, 3'b000, 5'd1, OP_R);

        memory[4] = rv_itype(12'd1, 5'd2, 3'b000, 5'd2, OP_I);

        memory[5] = rv_btype(13'b1_1111_1111_1000, 5'd3, 5'd2, 3'b100, OP_B);

        memory[6] = rv_stype(12'h100, 5'd1, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store;
        check(32'h100, 32'd15);

        test_num = 16;
        $display("\nTest %0d: Mixed program", test_num);
        init_memory;

        memory[0] = rv_itype(12'd10, 5'd0, 3'b000, 5'd1, OP_I);

        memory[1] = rv_itype(12'd20, 5'd0, 3'b000, 5'd2, OP_I);

        memory[2] = rv_rtype(7'b0000000, 5'd2, 5'd1, 3'b000, 5'd3, OP_R);

        memory[3] = rv_itype(12'b000000_000001, 5'd3, 3'b001, 5'd4, OP_I);

        memory[4] = rv_stype(12'h200, 5'd4, 5'd0, 3'b010, OP_S);

        memory[5] = rv_itype(12'h200, 5'd0, 3'b010, 5'd5, OP_L);

        memory[6] = rv_itype(12'd60, 5'd0, 3'b000, 5'd6, OP_I);

        memory[7] = rv_btype(13'd8, 5'd6, 5'd5, 3'b000, OP_B);

        memory[8] = rv_itype(12'd0, 5'd0, 3'b000, 5'd7, OP_I);

        memory[9] = rv_itype(12'd1, 5'd0, 3'b000, 5'd7, OP_I);

        memory[10] = rv_utype(20'hABCDE, 5'd8, OP_LUI);

        memory[11] = rv_itype(12'h123, 5'd8, 3'b110, 5'd8, OP_I);

        memory[12] = rv_stype(12'h100, 5'd5, 5'd0, 3'b010, OP_S);

        memory[13] = rv_stype(12'h104, 5'd7, 5'd0, 3'b010, OP_S);

        memory[14] = rv_stype(12'h108, 5'd8, 5'd0, 3'b010, OP_S);
        reset_cpu;
        wait_store;
        wait_store; check(32'h100, 32'd60);
        wait_store; check(32'h104, 32'd1);
        wait_store; check(32'h108, 32'hABCDE123);

        $display("\n============================================================");
        $display("TEST SUMMARY: %0d PASSED, %0d FAILED out of %0d total",
                 total_pass, total_fail, total_pass + total_fail);
        if (total_fail == 0)
            $display("ALL TESTS PASSED!");
        else
            $display("SOME TESTS FAILED!");
        $display("============================================================");
        $finish;
    end

    initial begin
        #1000000;
        $display("\n[TIMEOUT] Simulation exceeded 1ms - aborting");
        $finish;
    end

endmodule
