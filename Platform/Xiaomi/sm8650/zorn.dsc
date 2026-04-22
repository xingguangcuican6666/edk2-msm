[Defines]
  VENDOR_NAME                    = Xiaomi
  PLATFORM_NAME                  = zorn
  PLATFORM_GUID                  = c3f7a4d1-824b-48f5-b9ca-6b53fecdb3ff
  PLATFORM_VERSION               = 0.1
  DSC_SPECIFICATION              = 0x00010019
  OUTPUT_DIRECTORY               = Build/$(PLATFORM_NAME)
  SUPPORTED_ARCHITECTURES        = AARCH64
  BUILD_TARGETS                  = DEBUG|RELEASE
  SKUID_IDENTIFIER               = DEFAULT
  FLASH_DEFINITION               = Platform/Qualcomm/sm8650/sm8650.fdf
  DEVICE_DXE_FV_COMPONENTS       = Platform/Xiaomi/sm8650/zorn.fdf.inc

!include Platform/Qualcomm/sm8650/sm8650.dsc

[BuildOptions.common]
  GCC:*_*_AARCH64_CC_FLAGS = -DENABLE_SIMPLE_INIT

[PcdsFixedAtBuild.common]
  # Redmi K80 (zorn): 6.67" AMOLED 1220x2712 @ 144Hz
  gQcomTokenSpaceGuid.PcdMipiFrameBufferWidth|1220
  gQcomTokenSpaceGuid.PcdMipiFrameBufferHeight|2712

  # Simple Init
  gSimpleInitTokenSpaceGuid.PcdGuiDefaultDPI|446

  gRenegadePkgTokenSpaceGuid.PcdDeviceVendor|"Xiaomi"
  gRenegadePkgTokenSpaceGuid.PcdDeviceProduct|"Redmi K80"
  gRenegadePkgTokenSpaceGuid.PcdDeviceCodeName|"zorn"
