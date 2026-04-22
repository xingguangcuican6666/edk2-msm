#!/bin/bash
set -euo pipefail

usage() {
	echo "Usage: $0 --device DEVICE --payload FILE [--output FILE] [--mode MODE] [--base HEX] [--size HEX] [--entry-offset HEX] [--no-dtb]"
	echo
	echo "Package an external payload as an Android boot.img."
	echo
	echo "Modes:"
	echo "  bootshim     wrap the payload with BootShim and emit boot.img"
	echo "  kernel-image treat the payload as a prebuilt ARM64 kernel-style image and emit boot.img"
	echo
	echo "In bootshim mode, if FILE is an ELF executable with a single LOAD segment, the script will:"
	echo "  1. extract the loadable segment,"
	echo "  2. infer BootShim base/size from the ELF,"
	echo "  3. use the ELF entry point as a BootShim entry offset."
	echo
	echo "For raw payloads in bootshim mode, --base and --size are required."
	echo
	echo "Examples:"
	echo "  $0 --device zorn --payload UEFIFirmwareBackup/qcom-lanai/uefi_debug.elf"
	echo "  $0 --device zorn --payload wrapper/Image --mode kernel-image --no-dtb"
	echo "  $0 --device zorn --payload payload.bin --base 0xce000000 --size 0x02000000 --entry-offset 0x0"
}

error() {
	echo "$*" >&2
	exit 1
}

hex_to_dec() {
	local value="${1}"
	value="${value#0x}"
	printf '%u\n' "$((16#${value}))"
}

dec_to_hex() {
	printf '0x%x\n' "${1}"
}

align_up() {
	local value="${1}"
	local align="${2}"
	printf '%u\n' $((((value + align - 1) / align) * align))
}

ROOTDIR="$(realpath "$(dirname "$0")/..")"
cd "${ROOTDIR}"

DEVICE=""
PAYLOAD=""
OUTPUT=""
MODE="bootshim"
BOOTSHIM_BASE=""
BOOTSHIM_SIZE=""
BOOTSHIM_ENTRY_OFFSET="0x0"
APPEND_DTB=true

while [[ $# -gt 0 ]]; do
	case "${1}" in
		-d|--device)
			DEVICE="${2}"
			shift 2
			;;
		-p|--payload)
			PAYLOAD="${2}"
			shift 2
			;;
		-o|--output)
			OUTPUT="${2}"
			shift 2
			;;
		-m|--mode)
			MODE="${2}"
			shift 2
			;;
		--base)
			BOOTSHIM_BASE="${2}"
			shift 2
			;;
		--size)
			BOOTSHIM_SIZE="${2}"
			shift 2
			;;
		--entry-offset)
			BOOTSHIM_ENTRY_OFFSET="${2}"
			shift 2
			;;
		--no-dtb)
			APPEND_DTB=false
			shift
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			error "Unknown argument: ${1}"
			;;
	esac
done

[[ -n "${DEVICE}" ]] || error "Missing --device"
[[ -n "${PAYLOAD}" ]] || error "Missing --payload"
PAYLOAD="$(realpath "${PAYLOAD}")"
[[ -f "${PAYLOAD}" ]] || error "Payload not found: ${PAYLOAD}"

if [[ -f "configs/devices/${DEVICE}.conf" ]]; then
	source "configs/devices/${DEVICE}.conf"
else
	error "Device configuration not found: configs/devices/${DEVICE}.conf"
fi

typeset -l SOC_PLATFORM_L="${SOC_PLATFORM}"
if [[ -f "configs/${SOC_PLATFORM_L}.conf" ]]; then
	source "configs/${SOC_PLATFORM_L}.conf"
else
	error "SoC configuration not found: configs/${SOC_PLATFORM_L}.conf"
fi

# Re-source device config so device-specific overrides win.
source "configs/devices/${DEVICE}.conf"

if [[ -z "${OUTPUT}" ]]; then
	OUTPUT="${PWD}/boot-${DEVICE}-external.img"
else
	OUTPUT="$(realpath -m "${OUTPUT}")"
fi

TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

RAW_PAYLOAD="${TMPDIR}/payload.raw"
KERNEL_WITH_SHIM="${TMPDIR}/kernel-bootshim.bin"
KERNEL_GZ="${TMPDIR}/kernel.gz"
FINAL_KERNEL="${TMPDIR}/kernel"
EMPTY_RAMDISK="${TMPDIR}/ramdisk"
: > "${EMPTY_RAMDISK}"

case "${MODE}" in
	bootshim|kernel-image)
		;;
	*)
		error "Unsupported --mode: ${MODE}"
		;;
esac

PAYLOAD_TYPE="$(file -b "${PAYLOAD}")"
if [[ "${MODE}" == "bootshim" && "${PAYLOAD_TYPE}" == ELF* ]]; then
	LOAD_COUNT="$(readelf -lW "${PAYLOAD}" | awk '$1 == "LOAD" {c++} END {print c + 0}')"
	[[ "${LOAD_COUNT}" == "1" ]] || error "ELF payload must have exactly one LOAD segment, found ${LOAD_COUNT}"

	ENTRY_HEX="$(readelf -h "${PAYLOAD}" | awk '/Entry point address:/ {print $4; exit}')"
	read -r _ LOAD_OFFSET_HEX LOAD_VADDR_HEX _ LOAD_FILESZ_HEX LOAD_MEMSZ_HEX _ _ < <(
		readelf -lW "${PAYLOAD}" | awk '$1 == "LOAD" {print $1, $2, $3, $4, $5, $6, $7, $8; exit}'
	)

	ENTRY_DEC="$(hex_to_dec "${ENTRY_HEX}")"
	LOAD_OFFSET_DEC="$(hex_to_dec "${LOAD_OFFSET_HEX}")"
	LOAD_VADDR_DEC="$(hex_to_dec "${LOAD_VADDR_HEX}")"
	LOAD_FILESZ_DEC="$(hex_to_dec "${LOAD_FILESZ_HEX}")"
	LOAD_MEMSZ_DEC="$(hex_to_dec "${LOAD_MEMSZ_HEX}")"

	(( ENTRY_DEC >= LOAD_VADDR_DEC )) || error "ELF entry is below LOAD segment base"
	(( ENTRY_DEC < LOAD_VADDR_DEC + LOAD_MEMSZ_DEC )) || error "ELF entry is outside LOAD segment"

	ENTRY_OFFSET_DEC="$((ENTRY_DEC - LOAD_VADDR_DEC))"
	PAYLOAD_SIZE_DEC="$(align_up "${LOAD_MEMSZ_DEC}" 16)"

	dd if="${PAYLOAD}" of="${RAW_PAYLOAD}" bs=1 skip="${LOAD_OFFSET_DEC}" count="${LOAD_FILESZ_DEC}" status=none
	truncate -s "${PAYLOAD_SIZE_DEC}" "${RAW_PAYLOAD}"

	if [[ -z "${BOOTSHIM_BASE}" ]]; then
		BOOTSHIM_BASE="$(dec_to_hex "${LOAD_VADDR_DEC}")"
	fi
	if [[ -z "${BOOTSHIM_SIZE}" ]]; then
		BOOTSHIM_SIZE="$(dec_to_hex "${PAYLOAD_SIZE_DEC}")"
	fi
	BOOTSHIM_ENTRY_OFFSET="$(dec_to_hex "${ENTRY_OFFSET_DEC}")"
else
	if [[ "${MODE}" == "bootshim" ]]; then
		cp "${PAYLOAD}" "${RAW_PAYLOAD}"
		[[ -n "${BOOTSHIM_BASE}" ]] || error "Raw payload requires --base"
		[[ -n "${BOOTSHIM_SIZE}" ]] || error "Raw payload requires --size"

		RAW_SIZE_DEC="$(stat -c '%s' "${RAW_PAYLOAD}")"
		BOOTSHIM_SIZE_DEC="$(hex_to_dec "${BOOTSHIM_SIZE}")"
		(( RAW_SIZE_DEC <= BOOTSHIM_SIZE_DEC )) || error "Raw payload is larger than requested BootShim size"
		BOOTSHIM_SIZE_DEC="$(align_up "${BOOTSHIM_SIZE_DEC}" 16)"
		truncate -s "${BOOTSHIM_SIZE_DEC}" "${RAW_PAYLOAD}"
		BOOTSHIM_SIZE="$(dec_to_hex "${BOOTSHIM_SIZE_DEC}")"
	else
		cp "${PAYLOAD}" "${FINAL_KERNEL}"
	fi
fi

echo "Payload      : ${PAYLOAD}"
echo "Mode         : ${MODE}"
if [[ "${MODE}" == "bootshim" ]]; then
	echo "BootShim base: ${BOOTSHIM_BASE}"
	echo "BootShim size: ${BOOTSHIM_SIZE}"
	echo "Entry offset : ${BOOTSHIM_ENTRY_OFFSET}"
fi
echo "Output       : ${OUTPUT}"
echo "Append DTB   : ${APPEND_DTB}"

if [[ "${MODE}" == "bootshim" ]]; then
	pushd "${ROOTDIR}/tools/BootShim" >/dev/null
		rm -f BootShim.bin BootShim.elf
		make UEFI_BASE="${BOOTSHIM_BASE}" UEFI_SIZE="${BOOTSHIM_SIZE}" UEFI_ENTRY_OFFSET="${BOOTSHIM_ENTRY_OFFSET}"
	popd >/dev/null

	cat "${ROOTDIR}/tools/BootShim/BootShim.bin" "${RAW_PAYLOAD}" > "${KERNEL_WITH_SHIM}"
	gzip -c < "${KERNEL_WITH_SHIM}" > "${KERNEL_GZ}"
else
	gzip -c < "${FINAL_KERNEL}" > "${KERNEL_GZ}"
fi

DTB_PATH="${ROOTDIR}/Platform/${VENDOR_NAME}/${SOC_PLATFORM_L}/FdtBlob_compat/${PLATFORM_NAME}.dtb"
if "${APPEND_DTB}" && [[ -f "${DTB_PATH}" ]]; then
	cat "${KERNEL_GZ}" "${DTB_PATH}" > "${FINAL_KERNEL}"
else
	cp "${KERNEL_GZ}" "${FINAL_KERNEL}"
fi

python3 "${ROOTDIR}/tools/mkbootimg.py" \
	--kernel "${FINAL_KERNEL}" \
	--ramdisk "${EMPTY_RAMDISK}" \
	--kernel_offset 0x00000000 \
	--ramdisk_offset 0x00000000 \
	--tags_offset 0x00000000 \
	--os_version "${BOOTIMG_OS_VERSION}" \
	--os_patch_level "${BOOTIMG_OS_PATCH_LEVEL}" \
	--header_version "${BOOTIMG_HEADER_VERSION}" \
	-o "${OUTPUT}"

echo "Created ${OUTPUT}"
