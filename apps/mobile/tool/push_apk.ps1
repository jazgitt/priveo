# Builds the dev app and copies it to the Downloads folder of the phone
# plugged in by USB. Then open Files > Downloads on the phone and tap
# priveo-dev.apk to install it.
#
# From any folder:
#   powershell -ExecutionPolicy Bypass -File apps\mobile\tool\push_apk.ps1
# Against another API:
#   ... push_apk.ps1 -ApiUrl http://192.168.1.5:8000
#
# It builds a RELEASE app by default. A debug app is much slower to start (the
# phone shows a blank screen for 5 to 9 seconds before the first Flutter frame),
# so judge the splash screen and any speed on a release build. Add -Debug only
# when you need a debug build.
param(
    [string]$ApiUrl = "https://priveo-api.vercel.app",
    [switch]$Debug
)

$ErrorActionPreference = "Stop"
$mobile = Split-Path -Parent $PSScriptRoot
$mode = if ($Debug) { "debug" } else { "release" }
$apk = Join-Path $mobile "build\app\outputs\flutter-apk\app-dev-$mode.apk"

$adb = (Get-Command adb -ErrorAction SilentlyContinue).Source
if (-not $adb) { $adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe" }
if (-not (Test-Path $adb)) { throw "adb was not found. Install the Android SDK platform tools." }

$phones = @(& $adb devices | Select-String "`tdevice$")
if ($phones.Count -eq 0) { throw "No phone found. Plug it in and allow USB debugging." }
if ($phones.Count -gt 1) { throw "More than one phone or emulator is connected. Leave only one." }

Write-Host "Building the dev app ($mode) for $ApiUrl ..."
Push-Location $mobile
try {
    flutter build apk "--$mode" --flavor dev -t lib/main_dev.dart "--dart-define=API_BASE_URL=$ApiUrl"
    if ($LASTEXITCODE -ne 0) { throw "The build failed." }
}
finally { Pop-Location }

Write-Host "Copying to the phone ..."
& $adb push $apk /sdcard/Download/priveo-dev.apk
if ($LASTEXITCODE -ne 0) { throw "The copy failed." }

Write-Host ""
Write-Host "Done. On the phone: Files > Downloads > priveo-dev.apk > Install."
