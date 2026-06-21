`timescale 1ns / 1ps

module \25323045_riscv (
    input clk,

    output reg [31:0] mem_addr,
    output reg [31:0] mem_wdata,
    output reg [3:0] mem_wmask,
    input [31:0] mem_rdata,
    output reg mem_rstrb,
    input mem_rbusy,
    input mem_wbusy,

    input reset
);

    localparam [3:0]
        FETCH1 = 4'd0,
        FETCH2 = 4'd1,
        FETCH3 = 4'd2,
        DECODE = 4'd3,
        EXEC = 4'd4,
        MEM1 = 4'd5,
        MEM2 = 4'd6,
        MEM3 = 4'd7,
        WB = 4'd8,
        BRANCH = 4'd9,
        JUMP = 4'd10;

    localparam [6:0]
        OP_RTYPE = 7'b0110011,
        OP_IALU = 7'b0010011,
        OP_LOAD = 7'b0000011,
        OP_STORE = 7'b0100011,
        OP_BRANCH = 7'b1100011,
        OP_JAL = 7'b1101111,
        OP_JALR = 7'b1100111,
        OP_LUI = 7'b0110111,
        OP_AUIPC = 7'b0010111;

    reg [31:0] PC;
    reg [31:0] instr;
    reg [3:0] state;

    reg [31:0] regfile [0:31];

    wire [6:0] opcode = instr[6:0];
    wire [4:0] rd = instr[11:7];
    wire [2:0] funct3 = instr[14:12];
    wire [4:0] rs1 = instr[19:15];
    wire [4:0] rs2 = instr[24:20];
    wire [6:0] funct7 = instr[31:25];

    reg [31:0] rs1_val, rs2_val;

    wire [31:0] imm_i = {{20{instr[31]}}, instr[31:20]};
    wire [31:0] imm_s = {{20{instr[31]}}, instr[31:25], instr[11:7]};
    wire [31:0] imm_b = {{19{instr[31]}}, instr[31], instr[7], instr[30:25], instr[11:8], 1'b0};
    wire [31:0] imm_u = {instr[31:12], 12'b0};
    wire [31:0] imm_j = {{11{instr[31]}}, instr[31], instr[19:12], instr[20], instr[30:21], 1'b0};

    reg [31:0] alu_result;
    reg [31:0] alu_a, alu_b;

    always @(*) begin
        alu_a = rs1_val;
        alu_b = (opcode == OP_RTYPE) ? rs2_val : imm_i;

        case (funct3)
            3'b000: begin
                if (opcode == OP_RTYPE && funct7[5])
                    alu_result = alu_a - alu_b;
                else
                    alu_result = alu_a + alu_b;
            end
            3'b001: alu_result = alu_a << alu_b[4:0];
            3'b010: alu_result = ($signed(alu_a) < $signed(alu_b)) ? 32'd1 : 32'd0;
            3'b011: alu_result = (alu_a < alu_b) ? 32'd1 : 32'd0;
            3'b100: alu_result = alu_a ^ alu_b;
            3'b101: begin
                if (funct7[5])
                    alu_result = $signed(alu_a) >>> alu_b[4:0];
                else
                    alu_result = alu_a >> alu_b[4:0];
            end
            3'b110: alu_result = alu_a | alu_b;
            3'b111: alu_result = alu_a & alu_b;
            default: alu_result = 32'd0;
        endcase
    end

    reg branch_taken;

    always @(*) begin
        case (funct3)
            3'b000: branch_taken = (rs1_val == rs2_val);
            3'b001: branch_taken = (rs1_val != rs2_val);
            3'b100: branch_taken = ($signed(rs1_val) < $signed(rs2_val));
            3'b101: branch_taken = ($signed(rs1_val) >= $signed(rs2_val));
            3'b110: branch_taken = (rs1_val < rs2_val);
            3'b111: branch_taken = (rs1_val >= rs2_val);
            default: branch_taken = 1'b0;
        endcase
    end

    reg [31:0] exec_result;
    reg [31:0] mem_address;

    reg [31:0] load_data;
    wire [1:0] byte_offset = mem_address[1:0];

    always @(*) begin
        case (funct3)
            3'b000: begin
                case (byte_offset)
                    2'b00: load_data = {{24{mem_rdata[7]}}, mem_rdata[7:0]};
                    2'b01: load_data = {{24{mem_rdata[15]}}, mem_rdata[15:8]};
                    2'b10: load_data = {{24{mem_rdata[23]}}, mem_rdata[23:16]};
                    2'b11: load_data = {{24{mem_rdata[31]}}, mem_rdata[31:24]};
                endcase
            end
            3'b001: begin
                case (byte_offset[1])
                    1'b0: load_data = {{16{mem_rdata[15]}}, mem_rdata[15:0]};
                    1'b1: load_data = {{16{mem_rdata[31]}}, mem_rdata[31:16]};
                endcase
            end
            3'b010: begin
                load_data = mem_rdata;
            end
            3'b100: begin
                case (byte_offset)
                    2'b00: load_data = {24'b0, mem_rdata[7:0]};
                    2'b01: load_data = {24'b0, mem_rdata[15:8]};
                    2'b10: load_data = {24'b0, mem_rdata[23:16]};
                    2'b11: load_data = {24'b0, mem_rdata[31:24]};
                endcase
            end
            3'b101: begin
                case (byte_offset[1])
                    1'b0: load_data = {16'b0, mem_rdata[15:0]};
                    1'b1: load_data = {16'b0, mem_rdata[31:16]};
                endcase
            end
            default: load_data = mem_rdata;
        endcase
    end

    reg [31:0] store_data;
    reg [3:0] store_mask;
    wire [31:0] store_addr = rs1_val + imm_s;
    wire [1:0] store_offset = store_addr[1:0];

    always @(*) begin
        store_data = 32'd0;
        store_mask = 4'b0000;
        case (funct3)
            3'b000: begin
                case (store_offset)
                    2'b00: begin store_data = {24'b0, rs2_val[7:0]}; store_mask = 4'b0001; end
                    2'b01: begin store_data = {16'b0, rs2_val[7:0], 8'b0}; store_mask = 4'b0010; end
                    2'b10: begin store_data = {8'b0, rs2_val[7:0], 16'b0}; store_mask = 4'b0100; end
                    2'b11: begin store_data = {rs2_val[7:0], 24'b0}; store_mask = 4'b1000; end
                endcase
            end
            3'b001: begin
                case (store_offset[1])
                    1'b0: begin store_data = {16'b0, rs2_val[15:0]}; store_mask = 4'b0011; end
                    1'b1: begin store_data = {rs2_val[15:0], 16'b0}; store_mask = 4'b1100; end
                endcase
            end
            3'b010: begin
                store_data = rs2_val;
                store_mask = 4'b1111;
            end
            default: begin
                store_data = 32'd0;
                store_mask = 4'b0000;
            end
        endcase
    end

    integer i;

    always @(posedge clk) begin
        if (!reset) begin

            PC <= 32'd0;
            state <= FETCH1;
            instr <= 32'd0;
            mem_addr <= 32'd0;
            mem_wdata <= 32'd0;
            mem_wmask <= 4'b0000;
            mem_rstrb <= 1'b0;
            rs1_val <= 32'd0;
            rs2_val <= 32'd0;
            exec_result <= 32'd0;
            mem_address <= 32'd0;
            for (i = 0; i < 32; i = i + 1)
                regfile[i] <= 32'd0;
        end else begin
            case (state)

                FETCH1: begin
                    mem_addr <= PC;
                    mem_rstrb <= 1'b1;
                    mem_wmask <= 4'b0000;
                    state <= FETCH2;
                end

                FETCH2: begin
                    mem_rstrb <= 1'b0;
                    state <= FETCH3;
                end

                FETCH3: begin
                    instr <= mem_rdata;
                    state <= DECODE;
                end

                DECODE: begin
                    rs1_val <= (instr[19:15] == 5'd0) ? 32'd0 : regfile[instr[19:15]];
                    rs2_val <= (instr[24:20] == 5'd0) ? 32'd0 : regfile[instr[24:20]];
                    state <= EXEC;
                end

                EXEC: begin
                    case (opcode)
                        OP_RTYPE: begin
                            exec_result <= alu_result;
                            state <= WB;
                        end

                        OP_IALU: begin
                            exec_result <= alu_result;
                            state <= WB;
                        end

                        OP_LOAD: begin
                            mem_address <= rs1_val + imm_i;
                            state <= MEM1;
                        end

                        OP_STORE: begin
                            mem_address <= store_addr;
                            state <= MEM1;
                        end

                        OP_BRANCH: begin
                            state <= BRANCH;
                        end

                        OP_JAL: begin
                            exec_result <= PC + 32'd4;
                            state <= JUMP;
                        end

                        OP_JALR: begin
                            exec_result <= PC + 32'd4;
                            state <= JUMP;
                        end

                        OP_LUI: begin
                            exec_result <= imm_u;
                            state <= WB;
                        end

                        OP_AUIPC: begin
                            exec_result <= PC + imm_u;
                            state <= WB;
                        end

                        default: begin
                            state <= FETCH1;
                        end
                    endcase
                end

                MEM1: begin
                    if (opcode == OP_LOAD) begin
                        mem_addr <= {mem_address[31:2], 2'b00};
                        mem_rstrb <= 1'b1;
                        mem_wmask <= 4'b0000;
                        state <= MEM2;
                    end else begin
                        mem_addr <= {mem_address[31:2], 2'b00};
                        mem_wdata <= store_data;
                        mem_wmask <= store_mask;
                        mem_rstrb <= 1'b0;
                        state <= MEM2;
                    end
                end

                MEM2: begin
                    if (opcode == OP_STORE) begin
                        mem_wmask <= 4'b0000;
                    end
                    mem_rstrb <= 1'b0;
                    state <= MEM3;
                end

                MEM3: begin
                    if (opcode == OP_LOAD) begin

                        exec_result <= load_data;
                        state <= WB;
                    end else begin

                        PC <= PC + 32'd4;
                        state <= FETCH1;
                    end
                end

                WB: begin
                    if (rd != 5'd0) begin
                        regfile[rd] <= exec_result;
                    end
                    PC <= PC + 32'd4;
                    state <= FETCH1;
                end

                BRANCH: begin
                    if (branch_taken) begin
                        PC <= PC + imm_b;
                    end else begin
                        PC <= PC + 32'd4;
                    end
                    state <= FETCH1;
                end

                JUMP: begin
                    if (rd != 5'd0) begin
                        regfile[rd] <= exec_result;
                    end
                    if (opcode == OP_JAL) begin
                        PC <= PC + imm_j;
                    end else begin
                        PC <= (rs1_val + imm_i) & 32'hFFFFFFFE;
                    end
                    state <= FETCH1;
                end

                default: begin
                    state <= FETCH1;
                end

            endcase
        end
    end

endmodule
