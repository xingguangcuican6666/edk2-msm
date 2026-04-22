#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import io
import lzma
import struct
import sys
from pathlib import Path


BOOT_MAGIC = b"ANDROID!"
BOOT_HEADER_V3_PAGESIZE = 4096


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reuse a working Android boot wrapper kernel image and replace its "
            "embedded LZMA UEFI payload with a payload extracted from a Qualcomm UEFI ELF."
        )
    )
    parser.add_argument("--wrapper-bootimg", required=True, help="Reference boot.img that already boots")
    parser.add_argument("--uefi-payload", required=True, help="UEFI ELF or raw payload to embed")
    parser.add_argument("--output-kernel", required=True, help="Output patched raw kernel image")
    parser.add_argument(
        "--uefi-payload-format",
        choices=["auto", "elf-load-segment", "abl-inner-fv", "raw"],
        default="auto",
        help="How to interpret the payload before injecting it into the wrapper",
    )
    parser.add_argument(
        "--payload-lzma-offset",
        type=lambda x: int(x, 0),
        default=0x112D8,
        help="Offset of the embedded LZMA-alone payload inside the wrapper kernel image",
    )
    parser.add_argument(
        "--kernel-blob-offset",
        type=lambda x: int(x, 0),
        default=BOOT_HEADER_V3_PAGESIZE,
        help="Offset of the compressed kernel blob inside the wrapper boot image",
    )
    parser.add_argument(
        "--kernel-blob-size",
        type=lambda x: int(x, 0),
        default=None,
        help="Compressed kernel blob size. Defaults to boot header kernel_size",
    )
    parser.add_argument(
        "--dump-wrapper-kernel",
        help="Optional path to write the unmodified decompressed wrapper kernel image",
    )
    parser.add_argument(
        "--abl-lzma-offset",
        type=lambda x: int(x, 0),
        default=0x1078,
        help="Offset of the embedded ABL inner LZMA payload when --uefi-payload-format=abl-inner-fv",
    )
    return parser.parse_args()


def read_boot_kernel_blob(blob: bytes, kernel_blob_offset: int, kernel_blob_size: int | None) -> bytes:
    if blob[:8] != BOOT_MAGIC:
        raise ValueError("Wrapper image is not an Android boot image")

    header_kernel_size = struct.unpack_from("<I", blob, 8)[0]
    size = header_kernel_size if kernel_blob_size is None else kernel_blob_size
    end = kernel_blob_offset + size
    if end > len(blob):
        raise ValueError("Kernel blob extends beyond wrapper image")
    return blob[kernel_blob_offset:end]


def extract_elf_load_segment(blob: bytes) -> bytes:
    if blob[:4] != b"\x7fELF":
        return blob

    elf_class = blob[4]
    endian = "<" if blob[5] == 1 else ">"
    if elf_class == 1:
        e_phoff = struct.unpack_from(endian + "I", blob, 28)[0]
        e_phentsize = struct.unpack_from(endian + "H", blob, 42)[0]
        e_phnum = struct.unpack_from(endian + "H", blob, 44)[0]
        fmt = endian + "IIIIIIII"
        idx_type, idx_offset, idx_filesz, idx_memsz = 0, 1, 4, 5
    elif elf_class == 2:
        e_phoff = struct.unpack_from(endian + "Q", blob, 32)[0]
        e_phentsize = struct.unpack_from(endian + "H", blob, 54)[0]
        e_phnum = struct.unpack_from(endian + "H", blob, 56)[0]
        fmt = endian + "IIQQQQQQ"
        idx_type, idx_offset, idx_filesz, idx_memsz = 0, 2, 5, 6
    else:
        raise ValueError(f"Unsupported ELF class: {elf_class}")

    load_segments = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        vals = struct.unpack_from(fmt, blob, off)
        if vals[idx_type] == 1:
            load_segments.append(vals)

    if len(load_segments) != 1:
        raise ValueError(f"Expected exactly one PT_LOAD segment, found {len(load_segments)}")

    seg = load_segments[0]
    seg_off = seg[idx_offset]
    seg_filesz = seg[idx_filesz]
    seg_memsz = seg[idx_memsz]
    payload = bytearray(blob[seg_off : seg_off + seg_filesz])
    if seg_memsz > seg_filesz:
        payload.extend(b"\x00" * (seg_memsz - seg_filesz))
    return bytes(payload)


def extract_abl_inner_fv(blob: bytes, lzma_offset: int) -> bytes:
    if lzma_offset >= len(blob):
        raise ValueError("ABL LZMA offset is outside the payload")
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    inner = dec.decompress(blob[lzma_offset:])
    if b"_FVH" not in inner[:0x100]:
        raise ValueError("Decompressed ABL inner payload does not look like a FV image")
    return inner


def resolve_payload(blob: bytes, payload_format: str, abl_lzma_offset: int) -> bytes:
    if payload_format == "raw":
        return blob
    if payload_format == "elf-load-segment":
        return extract_elf_load_segment(blob)
    if payload_format == "abl-inner-fv":
        return extract_abl_inner_fv(blob, abl_lzma_offset)

    # auto
    if blob[:4] == b"\x7fELF":
        elf_class = blob[4]
        if elf_class == 1:
            try:
                return extract_abl_inner_fv(blob, abl_lzma_offset)
            except Exception:
                return extract_elf_load_segment(blob)
        return extract_elf_load_segment(blob)
    return blob


def main() -> int:
    args = parse_args()
    wrapper_boot = Path(args.wrapper_bootimg).read_bytes()
    kernel_blob = read_boot_kernel_blob(wrapper_boot, args.kernel_blob_offset, args.kernel_blob_size)
    wrapper_kernel = gzip.GzipFile(fileobj=io.BytesIO(kernel_blob)).read()

    if args.dump_wrapper_kernel:
        Path(args.dump_wrapper_kernel).write_bytes(wrapper_kernel)

    uefi_blob = resolve_payload(
        Path(args.uefi_payload).read_bytes(),
        args.uefi_payload_format,
        args.abl_lzma_offset,
    )
    replacement_lzma = lzma.compress(uefi_blob, format=lzma.FORMAT_ALONE, preset=9)

    available = len(wrapper_kernel) - args.payload_lzma_offset
    if available <= 0:
        raise ValueError("Wrapper kernel is smaller than the specified LZMA offset")
    if len(replacement_lzma) > available:
        raise ValueError(
            f"Compressed replacement payload too large: 0x{len(replacement_lzma):x} > 0x{available:x}"
        )

    patched = bytearray(wrapper_kernel)
    end = args.payload_lzma_offset + len(replacement_lzma)
    patched[args.payload_lzma_offset:end] = replacement_lzma
    patched[end:] = b"\x00" * (len(wrapper_kernel) - end)

    Path(args.output_kernel).write_bytes(patched)
    print(
        f"Wrote patched wrapper kernel to {args.output_kernel} "
        f"(wrapper 0x{len(wrapper_kernel):x}, payload 0x{len(uefi_blob):x}, lzma 0x{len(replacement_lzma):x})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
