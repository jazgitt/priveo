# Builds the dev app and copies it to the Downloads folder of the phone
# plugged in by USB. Then open Files > Downloads on the phone and tap
# priveo-dev-<version>.apk to install it.
#
# Every build gets a new version first (see tool\bump_version.ps1): 0.0.1,
# 0.0.2 and so on, so the phone always treats it as an update, and the version
# is in the file name and on the phone under Settings > Apps > Priveo.
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

# A new version for every build, before the build reads it.
& (Join-Path $PSScriptRoot "bump_version.ps1")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) { throw "The version could not be raised." }
$version = (Select-String -Path (Join-Path $mobile "pubspec.yaml") -Pattern '^version:\s*(\d+\.\d+\.\d+)').Matches[0].Groups[1].Value
$remote = "/sdcard/Download/priveo-dev-$version.apk"

Write-Host "Building the dev app $version ($mode) for $ApiUrl ..."
Push-Location $mobile
try {
    flutter build apk "--$mode" --flavor dev -t lib/main_dev.dart "--dart-define=API_BASE_URL=$ApiUrl"
    if ($LASTEXITCODE -ne 0) { throw "The build failed." }
}
finally { Pop-Location }

Write-Host "Copying to the phone ..."
& $adb push $apk $remote
if ($LASTEXITCODE -ne 0) { throw "The copy failed." }

Write-Host ""
Write-Host "Done. Version $version. On the phone: Files > Downloads > priveo-dev-$version.apk > Install."
