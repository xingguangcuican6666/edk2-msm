/** @file
  Minimal stub DXE driver that installs the AndroidBootImg protocol so that
  EmbeddedPkg/Application/AndroidBoot/AndroidBootApp can locate it.

  The protocol provides two optional callbacks used by AndroidBootImgLib:
    - AppendArgs  : append platform-specific kernel command-line arguments.
    - UpdateDtb   : patch the device tree before handing it to the kernel.

  Both are left as no-ops here; device-specific overrides can be added by
  creating a platform-level library that re-implements this driver.

  Copyright (c) 2024, edk2-msm contributors.
  SPDX-License-Identifier: BSD-2-Clause-Patent
**/

#include <Uefi.h>
#include <Library/DebugLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/UefiDriverEntryPoint.h>
#include <Protocol/AndroidBootImg.h>

STATIC
EFI_STATUS
EFIAPI
AndroidBootImgAppendArgs (
  IN CHAR16  *Args,
  IN UINTN    Size
  )
{
  return EFI_SUCCESS;
}

STATIC ANDROID_BOOTIMG_PROTOCOL  mAndroidBootImgProtocol = {
  AndroidBootImgAppendArgs, /* AppendArgs  */
  NULL                      /* UpdateDtb – not required */
};

EFI_STATUS
EFIAPI
AndroidBootImgDxeEntryPoint (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  EFI_STATUS  Status;

  Status = gBS->InstallMultipleProtocolInterfaces (
                  &ImageHandle,
                  &gAndroidBootImgProtocolGuid,
                  &mAndroidBootImgProtocol,
                  NULL
                  );
  if (EFI_ERROR (Status)) {
    DEBUG ((DEBUG_ERROR, "%a: failed to install AndroidBootImg protocol: %r\n",
            __FUNCTION__, Status));
  }

  return Status;
}
