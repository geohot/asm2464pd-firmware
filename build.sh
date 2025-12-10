#!/bin/bash
#
# ASM2464PD Firmware Build Script
# Uses Keil C51 compiler to build firmware
#

set -e

# Keil tools path
KEIL_BIN="$HOME/.wine/drive_c/Keil_v5/C51/BIN"
C51="wine $KEIL_BIN/C51.exe"
BL51="wine $KEIL_BIN/BL51.exe"
OH51="wine $KEIL_BIN/OH51.exe"

# Directories
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
KEIL_DIR="$PROJECT_ROOT/keil"
BUILD_DIR="$PROJECT_ROOT/build/keil"
INCLUDE_DIR="$KEIL_DIR/include"

# Original firmware for comparison
ORIGINAL_FW="$PROJECT_ROOT/fw.bin"

# Compiler flags
C51_FLAGS="OPTIMIZE(9,SIZE) INCDIR($INCLUDE_DIR)"

# Linker flags
# CODE(0x0000) places code starting at address 0x0000
BL51_FLAGS="CODE(0x0000) NODEFAULTLIBRARY"

# Create build directory
mkdir -p "$BUILD_DIR"

# Convert Windows path
win_path() {
    echo "Z:$1" | tr '/' '\\'
}

# Compile a single C file
compile() {
    local src="$1"
    local obj="${src%.c}.OBJ"

    echo "Compiling: $src"
    pushd "$(dirname "$src")" > /dev/null
    $C51 "$(basename "$src")" "$C51_FLAGS" 2>&1 | grep -v "^[0-9a-f]*:fixme:" || true
    popd > /dev/null
}

# Link object files (must be run from directory containing .OBJ files)
link() {
    local output="$1"
    shift
    local objs="$@"

    echo "Linking: $output"
    # Keil expects uppercase .OBJ extension
    local obj_upper=$(echo "$objs" | tr '[:lower:]' '[:upper:]' | sed 's/\.OBJ/.OBJ/g')
    # Use uppercase output name (Keil convention)
    local output_upper=$(basename "$output" | tr '[:lower:]' '[:upper:]')
    $BL51 "$obj_upper" "TO($output_upper)" "$BL51_FLAGS" 2>&1 | grep -v "^[0-9a-f]*:fixme:" || true
}

# Convert to hex
convert_hex() {
    local input="$1"

    echo "Converting to hex: $input"
    pushd "$(dirname "$input")" > /dev/null
    $OH51 "$(basename "${input%.*}")" 2>&1 | grep -v "^[0-9a-f]*:fixme:" || true
    popd > /dev/null
}

# Convert hex to binary
hex_to_bin() {
    local hex="$1"
    local bin="$2"
    local size="${3:-98064}"  # Default to fw.bin size (0x17F10)

    echo "Converting to binary: $bin"
    python3 -c "
import sys

data = bytearray($size)
with open('$hex', 'r') as f:
    for line in f:
        if not line.startswith(':'):
            continue
        line = line.strip()
        n = int(line[1:3], 16)
        addr = int(line[3:7], 16)
        t = int(line[7:9], 16)
        if t == 0:  # Data record
            for i in range(n):
                if addr + i < len(data):
                    data[addr + i] = int(line[9 + i*2:11 + i*2], 16)
        elif t == 2:  # Extended segment address
            pass  # TODO: handle segment addresses for bank 1
        elif t == 4:  # Extended linear address
            pass  # TODO: handle extended addresses

# Find actual end of data
end = len(data)
while end > 0 and data[end-1] == 0:
    end -= 1
end = min(end + 16, len(data))  # Add small padding

with open('$bin', 'wb') as f:
    f.write(bytes(data[:end]))

print(f'Binary size: {end} bytes')
"
}

# Build a test file
build_test() {
    local src="$1"
    local srcdir=$(cd "$(dirname "$src")" && pwd)
    local base=$(basename "${src%.c}")
    local base_upper=$(echo "$base" | tr '[:lower:]' '[:upper:]')

    # Create build output directory
    local builddir="$srcdir/build"
    mkdir -p "$builddir"

    echo "=== Building $base ==="

    # Copy source to build directory
    cp "$srcdir/$base.c" "$builddir/"

    # Change to build directory
    pushd "$builddir" > /dev/null

    # Compile (include path relative to build dir)
    echo "Compiling: $base.c"
    $C51 "$base.c" "OPTIMIZE(9,SIZE)" "INCDIR($srcdir/include)" 2>&1 | grep -v "^[0-9a-f]*:fixme:" || true

    # Link (Keil creates uppercase .OBJ, output name is derived from input)
    if [ -f "$base.OBJ" ]; then
        echo "Linking: $base_upper"
        $BL51 "$base.OBJ" "$BL51_FLAGS" 2>&1 | grep -v "^[0-9a-f]*:fixme:" || true
    fi

    # Convert to hex
    if [ -f "$base_upper" ]; then
        echo "Converting to hex: $base_upper"
        $OH51 "$base_upper" 2>&1 | grep -v "^[0-9a-f]*:fixme:" || true
    fi

    # Convert hex to binary (Keil creates uppercase .hex or lowercase depending on version)
    local hexfile=""
    if [ -f "$base_upper.hex" ]; then
        hexfile="$base_upper.hex"
    elif [ -f "$base.hex" ]; then
        hexfile="$base.hex"
    fi
    if [ -n "$hexfile" ]; then
        hex_to_bin "$hexfile" "$base.bin"
    fi

    # Clean up copied source
    rm -f "$base.c"

    popd > /dev/null

    echo "Output: $builddir/$base.bin"
}

# Compare built firmware with original
compare() {
    local built="$1"

    if [ ! -f "$ORIGINAL_FW" ]; then
        echo "Original firmware not found: $ORIGINAL_FW"
        return 1
    fi

    if [ ! -f "$built" ]; then
        echo "Built firmware not found: $built"
        return 1
    fi

    echo "=== Comparing with original firmware ==="
    echo "Original: $(stat -c %s "$ORIGINAL_FW") bytes"
    echo "Built:    $(stat -c %s "$built") bytes"

    # Use compare script if available
    if [ -f "$PROJECT_ROOT/compare/compare.py" ]; then
        python3 "$PROJECT_ROOT/compare/compare.py" "$ORIGINAL_FW" "$built"
    else
        # Simple comparison
        echo "First 64 bytes of original:"
        xxd -l 64 "$ORIGINAL_FW"
        echo ""
        echo "First 64 bytes of built:"
        xxd -l 64 "$built"
    fi
}

# Main entry point
main() {
    case "${1:-help}" in
        test)
            # Build a test file
            if [ -n "$2" ]; then
                build_test "$2"
            else
                echo "Usage: $0 test <file.c>"
            fi
            ;;

        compile)
            # Compile a single file
            if [ -n "$2" ]; then
                compile "$2"
            else
                echo "Usage: $0 compile <file.c>"
            fi
            ;;

        compare)
            # Compare with original firmware
            if [ -n "$2" ]; then
                compare "$2"
            else
                echo "Usage: $0 compare <firmware.bin>"
            fi
            ;;

        clean)
            # Clean build artifacts
            echo "Cleaning build artifacts..."
            rm -rf "$BUILD_DIR"
            find "$KEIL_DIR" -name "*.OBJ" -delete
            find "$KEIL_DIR" -name "*.LST" -delete
            find "$KEIL_DIR" -name "*.M51" -delete
            find "$KEIL_DIR" -name "*.hex" -delete
            find "$KEIL_DIR" -name "*.bin" -delete
            find "$KEIL_DIR" -type f ! -name "*.c" ! -name "*.h" ! -name "*.md" -delete 2>/dev/null || true
            ;;

        help|*)
            echo "ASM2464PD Firmware Build Script"
            echo ""
            echo "Usage: $0 <command> [args...]"
            echo ""
            echo "Commands:"
            echo "  test <file.c>      Build a test file (compile, link, convert)"
            echo "  compile <file.c>   Compile a single C file"
            echo "  compare <fw.bin>   Compare built firmware with original"
            echo "  clean              Clean build artifacts"
            echo "  help               Show this help"
            ;;
    esac
}

main "$@"
