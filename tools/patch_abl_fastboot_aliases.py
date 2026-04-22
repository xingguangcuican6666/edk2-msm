#!/usr/bin/env python3
from __future__ import annotations

import argparse
import lzma
import struct
import sys
from pathlib import Path


LZMA_OFFSET = 0x1078

# Entries are based on the current imgs/abl.elf build that still exposes
# unlock/lock handlers but only registers a subset of fastboot commands.
PATCHES = [
    {
        "name": "flashing unlock",
        "original": b"oem device-info\x00",
        "replacement": b"flashing unlock\x00",
        "handler_offset": 0x100C18,
        "handler_value": 0x9FA70,
        "critical": False,
    },
    {
        "name": "flashing lock",
        "original": b"oem audio-framework\x00",
        "replacement": b"flashing lock\x00",
        "handler_offset": 0x100D28,
        "handler_value": 0x9FDD8,
        "critical": False,
    },
    {
        "name": "flashing unlock_critical",
        "original": b"oem select-display-panel\x00",
        "replacement": b"flashing unlock_critical\x00",
        "handler_offset": 0x100BE8,
        "handler_value": 0x9FA70,
        "critical": True,
    },
    {
        "name": "flashing lock_critical",
        "original": b"oem set-hw-fence-value\x00",
        "replacement": b"flashing lock_critical\x00",
        "handler_offset": 0x100BF8,
        "handler_value": 0x9FDD8,
        "critical": True,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Patch a Qualcomm ABL outer ELF so it registers flashing "
            "unlock/lock aliases similar to the working 8e implementation."
        )
    )
    parser.add_argument("-i", "--input", required=True, help="Input ABL outer ELF")
    parser.add_argument("-o", "--output", required=True, help="Output patched ELF")
    parser.add_argument(
        "--lzma-offset",
        type=lambda x: int(x, 0),
        default=LZMA_OFFSET,
        help="Offset of the embedded LZMA-alone stream inside the ELF",
    )
    parser.add_argument(
        "--no-critical-aliases",
        action="store_true",
        help="Only add flashing unlock/lock aliases, leave critical aliases untouched",
    )
    parser.add_argument(
        "--dump-inner",
        help="Optional path to write the patched decompressed payload for inspection",
    )
    return parser.parse_args()


def get_load_file_limit(blob: bytes) -> int:
    if blob[:4] != b"\x7fELF":
        raise ValueError("Input is not an ELF file")

    elf_class = blob[4]
    endian = "<" if blob[5] == 1 else ">"
    if elf_class == 1:
        e_phoff = struct.unpack_from(endian + "I", blob, 28)[0]
        e_phentsize = struct.unpack_from(endian + "H", blob, 42)[0]
        e_phnum = struct.unpack_from(endian + "H", blob, 44)[0]
        fmt = endian + "IIIIIIII"
        p_type_index = 0
        p_offset_index = 1
        p_filesz_index = 4
    elif elf_class == 2:
        e_phoff = struct.unpack_from(endian + "Q", blob, 32)[0]
        e_phentsize = struct.unpack_from(endian + "H", blob, 54)[0]
        e_phnum = struct.unpack_from(endian + "H", blob, 56)[0]
        fmt = endian + "IIQQQQQQ"
        p_type_index = 0
        p_offset_index = 2
        p_filesz_index = 5
    else:
        raise ValueError(f"Unsupported ELF class: {elf_class}")

    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        values = struct.unpack_from(fmt, blob, off)
        if values[p_type_index] == 1:  # PT_LOAD
            return values[p_offset_index] + values[p_filesz_index]

    raise ValueError("No PT_LOAD segment found")


def decompress_lzma_alone(blob: bytes, start: int) -> tuple[bytes, int]:
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    payload = dec.decompress(blob[start:])
    consumed = len(blob[start:]) - len(dec.unused_data)
    if consumed <= 0:
        raise ValueError("Failed to consume any LZMA data")
    return payload, consumed


def patch_bytes_once(buf: bytearray, original: bytes, replacement: bytes) -> int:
    idx = bytes(buf).find(original)
    if idx < 0:
        raise ValueError(f"Pattern not found: {original!r}")
    if bytes(buf).find(original, idx + 1) >= 0:
        raise ValueError(f"Pattern is not unique: {original!r}")
    if len(replacement) > len(original):
        raise ValueError(f"Replacement longer than slot for {original!r}")
    padded = replacement + b"\x00" * (len(original) - len(replacement))
    buf[idx : idx + len(original)] = padded
    return idx


def patch_handler(buf: bytearray, offset: int, expected_old: int, new_value: int) -> None:
    current = struct.unpack_from("<Q", buf, offset)[0]
    if current != expected_old:
        raise ValueError(
            f"Unexpected handler at 0x{offset:x}: got 0x{current:x}, expected 0x{expected_old:x}"
        )
    struct.pack_into("<Q", buf, offset, new_value)


def main() -> int:
    args = parse_args()
    source = Path(args.input).read_bytes()
    limit = get_load_file_limit(source)
    if args.lzma_offset >= limit:
        raise ValueError("LZMA offset is outside the PT_LOAD file range")

    inner, consumed = decompress_lzma_alone(source, args.lzma_offset)
    patched = bytearray(inner)

    enabled_patches = [
        patch for patch in PATCHES if not (args.no_critical_aliases and patch["critical"])
    ]
    old_handlers = {
        "flashing unlock": 0xA0838,
        "flashing lock": 0xA1C6C,
        "flashing unlock_critical": 0xA02C4,
        "flashing lock_critical": 0xA0640,
    }

    print("Patching inner payload:")
    for patch in enabled_patches:
        string_off = patch_bytes_once(patched, patch["original"], patch["replacement"])
        patch_handler(
            patched,
            patch["handler_offset"],
            old_handlers[patch["name"]],
            patch["handler_value"],
        )
        print(
            f"  {patch['name']}: string 0x{string_off:x}, "
            f"handler 0x{patch['handler_offset']:x} -> 0x{patch['handler_value']:x}"
        )

    compressed = lzma.compress(bytes(patched), format=lzma.FORMAT_ALONE, preset=9)
    available = limit - args.lzma_offset
    if len(compressed) > available:
        raise ValueError(
            f"Recompressed payload too large: 0x{len(compressed):x} > 0x{available:x}"
        )

    out = bytearray(source)
    end = args.lzma_offset + len(compressed)
    out[args.lzma_offset:end] = compressed
    out[end:limit] = b"\x00" * (limit - end)

    Path(args.output).write_bytes(out)
    if args.dump_inner:
        Path(args.dump_inner).write_bytes(bytes(patched))

    print(
        f"Wrote patched ABL to {args.output} "
        f"(inner 0x{len(inner):x}, old LZMA 0x{consumed:x}, new LZMA 0x{len(compressed):x})"
    )
    if not args.no_critical_aliases:
        print(
            "Note: critical aliases reuse the same handlers as unlock/lock on this build, "
            "because this ABL already updates both normal and critical flags in those paths."
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI diagnostics
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
