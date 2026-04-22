#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import io
import lzma
import struct
import sys
from pathlib import Path


ABL_LZMA_OFFSET = 0x1078
WRAPPER_SLOT2_OFFSET = 0x18EEB0
WRAPPER_SLOT2_SIZE = 1232510


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Patch a Qualcomm UEFI wrapper ELF by replacing one embedded gzip FV slot "
            "with the inner FV extracted from a patched ABL outer ELF."
        )
    )
    parser.add_argument("--wrapper", required=True, help="Wrapper ELF, e.g. qcom-lanai/uefi_debug.elf")
    parser.add_argument("--abl", required=True, help="Patched ABL outer ELF or raw inner FV")
    parser.add_argument("--output", required=True, help="Patched wrapper output ELF")
    parser.add_argument(
        "--wrapper-slot-offset",
        type=lambda x: int(x, 0),
        default=WRAPPER_SLOT2_OFFSET,
        help="Offset of the gzip slot to replace inside the wrapper ELF",
    )
    parser.add_argument(
        "--wrapper-slot-size",
        type=lambda x: int(x, 0),
        default=WRAPPER_SLOT2_SIZE,
        help="Maximum size of the gzip slot inside the wrapper ELF",
    )
    parser.add_argument(
        "--abl-format",
        choices=["auto", "abl-outer", "raw-inner-fv"],
        default="auto",
        help="How to interpret the --abl input",
    )
    parser.add_argument(
        "--abl-lzma-offset",
        type=lambda x: int(x, 0),
        default=ABL_LZMA_OFFSET,
        help="Offset of the embedded LZMA stream when --abl-format=abl-outer",
    )
    parser.add_argument(
        "--dump-inner-fv",
        help="Optional path to write the ABL inner FV that was injected into the wrapper",
    )
    return parser.parse_args()


def read_abl_inner(blob: bytes, fmt: str, lzma_offset: int) -> bytes:
    if fmt == "raw-inner-fv":
        return blob

    if fmt == "auto":
        if blob[:4] == b"\x7fELF" and blob[4] == 1:
            fmt = "abl-outer"
        else:
            return blob

    if fmt != "abl-outer":
        raise ValueError(f"Unsupported ABL format: {fmt}")

    dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    inner = dec.decompress(blob[lzma_offset:])
    if b"_FVH" not in inner[:0x100]:
        raise ValueError("ABL inner payload does not look like a FV image")
    return inner


def gzip_blob(blob: bytes) -> bytes:
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as gz:
        gz.write(blob)
    return out.getvalue()


def main() -> int:
    args = parse_args()

    wrapper = bytearray(Path(args.wrapper).read_bytes())
    abl_inner = read_abl_inner(Path(args.abl).read_bytes(), args.abl_format, args.abl_lzma_offset)
    replacement = gzip_blob(abl_inner)

    if len(replacement) > args.wrapper_slot_size:
        raise ValueError(
            f"Compressed replacement payload too large: 0x{len(replacement):x} > 0x{args.wrapper_slot_size:x}"
        )
    if args.wrapper_slot_offset + args.wrapper_slot_size > len(wrapper):
        raise ValueError("Wrapper slot exceeds wrapper file size")

    end = args.wrapper_slot_offset + len(replacement)
    slot_end = args.wrapper_slot_offset + args.wrapper_slot_size
    wrapper[args.wrapper_slot_offset:end] = replacement
    wrapper[end:slot_end] = b"\x00" * (slot_end - end)

    Path(args.output).write_bytes(wrapper)
    if args.dump_inner_fv:
        Path(args.dump_inner_fv).write_bytes(abl_inner)

    print(
        f"Wrote patched wrapper to {args.output} "
        f"(inner FV 0x{len(abl_inner):x}, gzip 0x{len(replacement):x}, slot 0x{args.wrapper_slot_size:x})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
