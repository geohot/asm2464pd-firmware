#!/bin/bash
#
# ASM2464PD Firmware Build Script - SDCC Assembly
# Reconstructs fw.bin exactly using SDCC inline assembly
#

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ASM_DIR="$PROJECT_ROOT/asm"
SRC_DIR="$ASM_DIR/src"
BUILD_DIR="$ASM_DIR/build"
ORIGINAL_FW="$PROJECT_ROOT/fw.bin"

# Create build directory
mkdir -p "$BUILD_DIR"

# Bank 0 modules in order (for modular source)
BANK0_MODULES=(
    vectors
    isr
    math
    handlers
    usb
    cmd
    dma
    main
    scsi
    data
    power
    timer
    protocol
    util
    vendor
    error
    dispatch
    misc
)

# Bank 1 modules in order
BANK1_MODULES=(
    b1_handlers
    b1_protocol
    b1_util
    b1_misc
)

# Concatenate modules into a single assembly file (for modular source)
concat_modules() {
    local output="$1"
    shift
    local modules=("$@")

    echo "Concatenating modules..."
    > "$output"

    for mod in "${modules[@]}"; do
        if [ -f "$SRC_DIR/$mod.asm" ]; then
            echo "  + $mod.asm"
            cat "$SRC_DIR/$mod.asm" >> "$output"
            echo "" >> "$output"
        fi
    done
}

# Assemble a file to Intel HEX
assemble_to_ihx() {
    local src="$1"
    local base=$(basename "${src%.asm}")
    local rel="$BUILD_DIR/${base}.rel"
    local ihx="$BUILD_DIR/${base}.ihx"

    echo "Assembling: $(basename $src)"
    sdas8051 -plosgff "$rel" "$src"

    echo "Linking: $(basename $ihx)"
    sdld -i "$ihx" "$rel"
}

# Convert Intel HEX to binary at specific offset
hex_to_bin_offset() {
    local hex="$1"
    local bin="$2"
    local offset="${3:-0}"
    local size="${4:-65536}"

    echo "Converting: $(basename $hex) -> $(basename $bin)"

    python3 << EOF
data = bytearray($size)
with open('$hex', 'r') as f:
    base_addr = 0
    for line in f:
        if not line.startswith(':'):
            continue
        line = line.strip()
        n = int(line[1:3], 16)
        addr = int(line[3:7], 16)
        t = int(line[7:9], 16)
        if t == 0:  # Data record
            full_addr = base_addr + addr - $offset
            for i in range(n):
                if 0 <= full_addr + i < len(data):
                    data[full_addr + i] = int(line[9 + i*2:11 + i*2], 16)
        elif t == 2:  # Extended segment address
            base_addr = int(line[9:13], 16) << 4
        elif t == 4:  # Extended linear address
            base_addr = int(line[9:13], 16) << 16

with open('$bin', 'wb') as f:
    f.write(bytes(data))
print(f'  Size: {len(data)} bytes')
EOF
}

# Combine bank 0 and bank 1 binaries
combine_banks() {
    local bank0="$1"
    local bank1="$2"
    local output="$3"
    local total_size="${4:-98012}"

    echo "Combining banks..."

    python3 << EOF
with open('$bank0', 'rb') as f:
    bank0_data = f.read()
with open('$bank1', 'rb') as f:
    bank1_data = f.read()

combined = bytearray($total_size)
for i, b in enumerate(bank0_data):
    if i < len(combined):
        combined[i] = b
bank1_offset = 0x10000
for i, b in enumerate(bank1_data):
    if bank1_offset + i < len(combined):
        combined[bank1_offset + i] = b

with open('$output', 'wb') as f:
    f.write(bytes(combined))
print(f'  Combined: {len(combined)} bytes')
EOF
}

# Compare with original firmware
compare() {
    local built="$1"

    echo ""
    echo "=== Comparing with original firmware ==="
    echo "Original: $(stat -c %s "$ORIGINAL_FW") bytes"
    echo "Built:    $(stat -c %s "$built") bytes"

    if cmp -s "$ORIGINAL_FW" "$built"; then
        echo ""
        echo "✓ SUCCESS: Files are byte-for-byte identical!"
        return 0
    else
        echo ""
        echo "✗ DIFFERENCE: Files differ!"
        python3 << EOF
with open('$ORIGINAL_FW', 'rb') as f1, open('$built', 'rb') as f2:
    orig = f1.read()
    built = f2.read()

    min_len = min(len(orig), len(built))
    diff_count = 0
    first_diff = None
    for i in range(min_len):
        if orig[i] != built[i]:
            if first_diff is None:
                first_diff = i
            diff_count += 1
            if diff_count <= 10:
                print(f"  0x{i:05x}: expected 0x{orig[i]:02x}, got 0x{built[i]:02x}")

    if first_diff is not None:
        print(f"\nFirst difference at 0x{first_diff:05x}")
        print(f"Total bytes different: {diff_count}")

    if len(orig) != len(built):
        print(f"Size mismatch: expected {len(orig)}, got {len(built)}")
EOF
        return 1
    fi
}

# Check if modular source exists
has_modular_src() {
    [ -d "$SRC_DIR" ] && [ -f "$SRC_DIR/vectors.asm" ]
}

# Check if single-file source exists (preferred)
has_single_src() {
    [ -f "$ASM_DIR/bank0.asm" ] && [ -f "$ASM_DIR/bank1.asm" ]
}

# Legacy alias
has_legacy_src() {
    has_single_src
}

# Build from modular source
build_modular() {
    echo "=== Building from modular source ==="
    echo ""

    # Concatenate bank 0 modules
    concat_modules "$BUILD_DIR/bank0_combined.asm" "${BANK0_MODULES[@]}"

    # Concatenate bank 1 modules
    concat_modules "$BUILD_DIR/bank1_combined.asm" "${BANK1_MODULES[@]}"

    echo ""

    # Assemble bank 0
    assemble_to_ihx "$BUILD_DIR/bank0_combined.asm"
    mv "$BUILD_DIR/bank0_combined.rel" "$BUILD_DIR/bank0.rel"
    mv "$BUILD_DIR/bank0_combined.ihx" "$BUILD_DIR/bank0.ihx"

    # Convert bank 0
    hex_to_bin_offset "$BUILD_DIR/bank0.ihx" "$BUILD_DIR/bank0.bin" 0 65536

    # Assemble bank 1
    assemble_to_ihx "$BUILD_DIR/bank1_combined.asm"
    mv "$BUILD_DIR/bank1_combined.rel" "$BUILD_DIR/bank1.rel"
    mv "$BUILD_DIR/bank1_combined.ihx" "$BUILD_DIR/bank1.ihx"

    # Convert bank 1
    hex_to_bin_offset "$BUILD_DIR/bank1.ihx" "$BUILD_DIR/bank1.bin" 0x8000 32476

    # Combine
    combine_banks "$BUILD_DIR/bank0.bin" "$BUILD_DIR/bank1.bin" "$BUILD_DIR/fw.bin"

    echo ""
    echo "Output: $BUILD_DIR/fw.bin"

    compare "$BUILD_DIR/fw.bin"
}

# Build from legacy single files
build_legacy() {
    echo "=== Building from legacy source ==="
    echo ""

    # Assemble bank 0
    assemble_to_ihx "$ASM_DIR/bank0.asm"
    hex_to_bin_offset "$BUILD_DIR/bank0.ihx" "$BUILD_DIR/bank0.bin" 0 65536

    # Assemble bank 1
    assemble_to_ihx "$ASM_DIR/bank1.asm"
    hex_to_bin_offset "$BUILD_DIR/bank1.ihx" "$BUILD_DIR/bank1.bin" 0x8000 32476

    # Combine
    combine_banks "$BUILD_DIR/bank0.bin" "$BUILD_DIR/bank1.bin" "$BUILD_DIR/fw.bin"

    echo ""
    echo "Output: $BUILD_DIR/fw.bin"

    compare "$BUILD_DIR/fw.bin"
}

# Build all
build() {
    if has_single_src; then
        build_legacy
    elif has_modular_src; then
        build_modular
    else
        echo "No source files found!"
        echo "Run './build.sh regen' to create single-file source from fw.bin"
        echo "Or run './build.sh split' to create modular source"
        exit 1
    fi
}

# Split bank files into function-based modules
split() {
    echo "=== Splitting bank files into modules ==="
    if ! has_single_src; then
        echo "Single-file source not found. Running regen first..."
        regen
    fi
    python3 "$ASM_DIR/split_by_func.py"
    echo ""
    echo "Modular source created in: $SRC_DIR/"
    echo "Run './build.sh modular' to build from modules"
}

# Regenerate single-file source with real instructions
regen() {
    echo "=== Regenerating single-file source ==="
    python3 "$ASM_DIR/gen_bank.py"
}

# Clean build artifacts
clean() {
    echo "Cleaning build artifacts..."
    rm -rf "$BUILD_DIR"
}

# Deep clean - remove all generated files
distclean() {
    echo "Deep cleaning..."
    rm -rf "$BUILD_DIR"
    rm -rf "$SRC_DIR"
    rm -f "$ASM_DIR/bank0.asm" "$ASM_DIR/bank1.asm"
}

# Show help
help() {
    echo "ASM2464PD Firmware Build System"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build      Build firmware (default, prefers single-file source)"
    echo "  modular    Build from modular source (src/*.asm)"
    echo "  regen      Regenerate single-file source with real 8051 assembly"
    echo "  split      Split single-file source into function-based modules"
    echo "  compare    Compare built firmware with original"
    echo "  clean      Remove build artifacts"
    echo "  distclean  Remove all generated files"
    echo "  help       Show this help"
    echo ""
    echo "Source structure:"
    echo "  Single-file: bank0.asm, bank1.asm (preferred - real assembly)"
    echo "  Modular:     src/*.asm (split by function)"
}

# Main
case "${1:-build}" in
    build)
        build
        ;;
    modular)
        if has_modular_src; then
            build_modular
        else
            echo "Modular source not found in $SRC_DIR/"
            echo "Run './build.sh split' to create modular source"
            exit 1
        fi
        ;;
    split)
        split
        ;;
    regen)
        regen
        ;;
    compare)
        if [ -n "$2" ]; then
            compare "$2"
        else
            compare "$BUILD_DIR/fw.bin"
        fi
        ;;
    clean)
        clean
        ;;
    distclean)
        distclean
        ;;
    help|--help|-h)
        help
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac
