#include <Base.h>
#include <Guid/SmBios.h>
#include <IndustryStandard/SmBios.h>
#include <Protocol/Smbios.h>
#include <Library/SOCSmbiosInfoLib.h>

/***********************************************************************
        SMBIOS data definition  TYPE4  Processor Information
        SM8650 (Snapdragon 8 Gen 3): 1x X4 + 5x A720 + 2x A520
************************************************************************/
SMBIOS_TABLE_TYPE4 mProcessorInfoType4_x4 = {
    {EFI_SMBIOS_TYPE_PROCESSOR_INFORMATION, sizeof(SMBIOS_TABLE_TYPE4), 0},
    1,                // Socket String
    CentralProcessor, // ProcessorType;
    ProcessorFamilyIndicatorFamily2,
    2,                // ProcessorManufacture String;
    {
     {0x00, 0x00, 0x00, 0x00},
     {0x00, 0x00, 0x00, 0x00}},
    3, // ProcessorVersion String;
    {
        1  // ProcessorVoltageIndicateLegacy :1;
    },
    0,                     // ExternalClock;
    3300,                  // MaxSpeed;
    3300,                  // CurrentSpeed;
    0x41,                  // Status;
    ProcessorUpgradeOther,
    0,                     // L1CacheHandle;
    0,                     // L2CacheHandle;
    0xFFFF,                // L3CacheHandle;
    0,                     // SerialNumber;
    0,                     // AssetTag;
    7,                     // PartNumber;
    1,                     // CoreCount;
    1,                     // EnabledCoreCount;
    0,                     // ThreadCount;
    0xEC,
    ProcessorFamilyARM,
    0,
    0,
    0,
};

SMBIOS_TABLE_TYPE4 mProcessorInfoType4_a720_hi = {
    {EFI_SMBIOS_TYPE_PROCESSOR_INFORMATION, sizeof(SMBIOS_TABLE_TYPE4), 0},
    1,                // Socket String
    CentralProcessor,
    ProcessorFamilyIndicatorFamily2,
    2,                // ProcessorManufacture String;
    {
     {0x00, 0x00, 0x00, 0x00},
     {0x00, 0x00, 0x00, 0x00}},
    3, // ProcessorVersion String;
    {
        1  // ProcessorVoltageIndicateLegacy :1;
    },
    0,                     // ExternalClock;
    3150,                  // MaxSpeed;
    3150,                  // CurrentSpeed;
    0x41,                  // Status;
    ProcessorUpgradeOther,
    0,
    0,
    0xFFFF,
    0,
    0,
    6,                     // PartNumber;
    3,                     // CoreCount;
    3,                     // EnabledCoreCount;
    0,
    0xEC,
    ProcessorFamilyARM,
    0,
    0,
    0,
};

SMBIOS_TABLE_TYPE4 mProcessorInfoType4_a720_lo = {
    {EFI_SMBIOS_TYPE_PROCESSOR_INFORMATION, sizeof(SMBIOS_TABLE_TYPE4), 0},
    1,                // Socket String
    CentralProcessor,
    ProcessorFamilyIndicatorFamily2,
    2,                // ProcessorManufacture String;
    {
     {0x00, 0x00, 0x00, 0x00},
     {0x00, 0x00, 0x00, 0x00}},
    3, // ProcessorVersion String;
    {
        1  // ProcessorVoltageIndicateLegacy :1;
    },
    0,                     // ExternalClock;
    2960,                  // MaxSpeed;
    2960,                  // CurrentSpeed;
    0x41,                  // Status;
    ProcessorUpgradeOther,
    0,
    0,
    0xFFFF,
    0,
    0,
    5,                     // PartNumber;
    2,                     // CoreCount;
    2,                     // EnabledCoreCount;
    0,
    0xEC,
    ProcessorFamilyARM,
    0,
    0,
    0,
};

SMBIOS_TABLE_TYPE4 mProcessorInfoType4_a520 = {
    {EFI_SMBIOS_TYPE_PROCESSOR_INFORMATION, sizeof(SMBIOS_TABLE_TYPE4), 0},
    1,                // Socket String
    CentralProcessor,
    ProcessorFamilyIndicatorFamily2,
    2,                // ProcessorManufacture String;
    {
     {0x00, 0x00, 0x00, 0x00},
     {0x00, 0x00, 0x00, 0x00}},
    3, // ProcessorVersion String;
    {
        1  // ProcessorVoltageIndicateLegacy :1;
    },
    0,                     // ExternalClock;
    2270,                  // MaxSpeed;
    2270,                  // CurrentSpeed;
    0x41,                  // Status;
    ProcessorUpgradeOther,
    0,
    0,
    0xFFFF,
    0,
    0,
    4,                     // PartNumber;
    2,                     // CoreCount;
    2,                     // EnabledCoreCount;
    0,
    0xEC,
    ProcessorFamilyARM,
    0,
    0,
    0,
};

CHAR8 mCpuName[128] = "Qualcomm Snapdragon 8 Gen 3";

CHAR8 *mProcessorInfoType4Strings[] = {
    "BGA", "Qualcomm", "Snapdragon 8 Gen 3", "Cortex-X4", "Cortex-A520",
    "Cortex-A720 (2.96GHz)", "Cortex-A720 (3.15GHz)", "Cortex-X4 (3.3GHz)", NULL};

/***********************************************************************
        SMBIOS data definition  TYPE7  Cache Information
************************************************************************/
SMBIOS_TABLE_TYPE7 mCacheInfoType7 = {
    {EFI_SMBIOS_TYPE_CACHE_INFORMATION, sizeof(SMBIOS_TABLE_TYPE7), 0},
    3,      // SocketDesignation String
    0x0181, // Cache Configuration (L2, Internal, Enabled, WB)
    0x0400, // Maximum Size
    0x0400, // Install Size
    {0, 0, 1, 0, 0, 0, 0, 0},  // Supported SRAM Type (NonBurst)
    {0, 0, 1, 0, 0, 0, 0, 0},  // Current SRAM Type
    0,
    CacheErrorSingleBit,
    CacheTypeUnified,
    CacheAssociativity16Way
};
CHAR8 *mCacheInfoType7Strings[] = {"L1 Instruction", "L1 Data", "L2", NULL};

/***********************************************************************
        SMBIOS data definition  TYPE17  Memory Device Information
************************************************************************/
SMBIOS_TABLE_TYPE17 mMemDevInfoType17 = {
    {EFI_SMBIOS_TYPE_MEMORY_DEVICE, sizeof(SMBIOS_TABLE_TYPE17), 0},
    0,      // MemoryArrayHandle; initialized at runtime
    0xFFFE, // MemoryErrorInformationHandle;
    64,     // TotalWidth;
    64,     // DataWidth;
    0x2000, // Size; initialized at runtime
    MemoryFormFactorRowOfChips,
    0,
    1,      // DeviceLocator String
    2,      // BankLocator String
    MemoryTypeLpddr5, // LPDDR5X (reported as LPDDR5)
    {
        0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 1, 0, // Unbuffered
    },
    4800,   // Speed;
    2,      // Manufacturer String
    0,      // SerialNumber String
    0,      // AssetTag String
    0,      // PartNumber String
    0,      // Attributes;
    0,      // ExtendedSize;
    0,      // ConfiguredMemoryClockSpeed;
    0,      // MinimumVoltage;
    0,      // MaximumVoltage;
    0,      // ConfiguredVoltage;
    MemoryTechnologyDram,
    {{
        // MemoryOperatingModeCapability
        0, // Reserved                        :1;
        0, // Other                           :1;
        0, // Unknown                         :1;
        1, // VolatileMemory                  :1;
        0, // ByteAccessiblePersistentMemory  :1;
        0, // BlockAccessiblePersistentMemory :1;
        0  // Reserved                        :10;
    }},
    0,
    0,
    0,
    0,
    0,
    0xFFFFFFFFFFFFFFFFULL,  // VolatileSize; initialized at runtime
    0,
    0,
    0,
    0
};
CHAR8 *mMemDevInfoType17Strings[] = {"Builtin", "BANK 0", NULL};

VOID RegisterSOCSmbiosInfo(
	SMBIOS_LOG_SMBIOS_DATA LogSmbiosData,
	EFI_SMBIOS_HANDLE Type16
){
  EFI_SMBIOS_HANDLE SmbiosHandle;
  // TYPE7 Cache Information
  LogSmbiosData(
      (EFI_SMBIOS_TABLE_HEADER *)&mCacheInfoType7,
      mCacheInfoType7Strings, &SmbiosHandle);
  mProcessorInfoType4_x4.L2CacheHandle       = (UINT16)SmbiosHandle;
  mProcessorInfoType4_a720_hi.L2CacheHandle  = (UINT16)SmbiosHandle;
  mProcessorInfoType4_a720_lo.L2CacheHandle  = (UINT16)SmbiosHandle;
  mProcessorInfoType4_a520.L2CacheHandle     = (UINT16)SmbiosHandle;

  // TYPE4 Processor Information
  LogSmbiosData(
      (EFI_SMBIOS_TABLE_HEADER *)&mProcessorInfoType4_x4,
      mProcessorInfoType4Strings, NULL);
  LogSmbiosData(
      (EFI_SMBIOS_TABLE_HEADER *)&mProcessorInfoType4_a720_hi,
      mProcessorInfoType4Strings, NULL);
  LogSmbiosData(
      (EFI_SMBIOS_TABLE_HEADER *)&mProcessorInfoType4_a720_lo,
      mProcessorInfoType4Strings, NULL);
  LogSmbiosData(
      (EFI_SMBIOS_TABLE_HEADER *)&mProcessorInfoType4_a520,
      mProcessorInfoType4Strings, NULL);

  // TYPE17 Memory Device Information
  mMemDevInfoType17.MemoryArrayHandle    = Type16;
  LogSmbiosData(
      (EFI_SMBIOS_TABLE_HEADER *)&mMemDevInfoType17, mMemDevInfoType17Strings,
      NULL);
}
