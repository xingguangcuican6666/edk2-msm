ARCH              = arm64
TARGET            = aarch64-linux-gnu
CROSS_COMPILE     = $(TARGET)-
CC                = $(CROSS_COMPILE)gcc
OBJCOPY           = $(CROSS_COMPILE)objcopy
UEFI_ENTRY_OFFSET ?= 0

all: BootShim.elf BootShim.bin BootShim.Dualboot.elf BootShim.Dualboot.bin

BootShim.bin: BootShim.elf
	$(OBJCOPY) -O binary $< $@

BootShim.elf: BootShim.S
	$(CC) -c $< -o $@ -DUEFI_BASE=$(UEFI_BASE) -DUEFI_SIZE=$(UEFI_SIZE) -DUEFI_ENTRY_OFFSET=$(UEFI_ENTRY_OFFSET)

BootShim.Dualboot.bin: BootShim.Dualboot.elf
	$(OBJCOPY) -O binary $< $@

BootShim.Dualboot.elf: BootShim.Dualboot.S
	$(CC) -c $< -o $@ -DUEFI_BASE=$(UEFI_BASE) -DUEFI_SIZE=$(UEFI_SIZE) -DUEFI_ENTRY_OFFSET=$(UEFI_ENTRY_OFFSET)

BootShim.S:

BootShim.Dualboot.S:
