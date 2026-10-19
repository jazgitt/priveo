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
#
# Analytics (PostHog EU). The key is public by design, but it is not kept in
# the repo. Set it once for your user, or pass it for one build:
#   setx POSTHOG_KEY phc_xxx          (then open a new terminal)
#   ... push_apk.ps1 -PosthogKey phc_xxx
# Without a key the app sends nothing. Session replay is off unless you add
# -Replay (every signed-in role: customer, crew and admin).
param(
    [string]$ApiUrl = "https://priveo-api.vercel.app",
    [switch]$Debug,
    [string]$PosthogKey = $env:POSTHOG_KEY,
    [switch]$Replay
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

# A unique stamp for this run, compiled into the app. After the build the
# script looks for it inside the APK: old code cannot contain it.
$stamp = Get-Date -Format "yyMMdd-HHmmss"
$defines = @("--dart-define=API_BASE_URL=$ApiUrl", "--dart-define=BUILD_STAMP=$stamp")
if ($PosthogKey) {
    $defines += "--dart-define=POSTHOG_KEY=$PosthogKey"
    $defines += "--dart-define=POSTHOG_HOST=https://eu.i.posthog.com"
    $defines += "--dart-define=POSTHOG_REPLAY=$(if ($Replay) { 'true' } else { 'false' })"
    Write-Host "Analytics: PostHog EU, replay $(if ($Replay) { 'ON' } else { 'off' })"
} else {
    Write-Host "Analytics: off (no POSTHOG_KEY)"
}

Write-Host "Building the dev app $version ($mode) for $ApiUrl ..."
Push-Location $mobile
try {
    # Gradle once packed an old copy of the app's code into every APK, so new
    # code never reached the phone. These folders only hold packed copies of
    # the compiled app and are rebuilt in seconds, so clear them every time.
    foreach ($d in "merged_jni_libs", "merged_native_libs", "stripped_native_libs") {
        Remove-Item -Recurse -Force (Join-Path $mobile "build\app\intermediates\$d") -ErrorAction SilentlyContinue
    }
    flutter build apk "--$mode" --flavor dev -t lib/main_dev.dart @defines
    if ($LASTEXITCODE -ne 0) { throw "The build failed." }
}
finally { Pop-Location }

# Prove the APK holds the code compiled in this run. The stamp is new every
# run, so an APK packed from an old copy of the code cannot contain it.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($apk)
try {
    $entry = $zip.GetEntry("lib/arm64-v8a/libapp.so")
    $ms = New-Object System.IO.MemoryStream
    $s = $entry.Open(); $s.CopyTo($ms); $s.Dispose()
    # ISO-8859-1 (Latin1) keeps one char per byte. Windows PowerShell 5.1
    # has no [Encoding]::Latin1, so ask for it by code page.
    $text = [System.Text.Encoding]::GetEncoding(28591).GetString($ms.ToArray())
}
finally { $zip.Dispose() }
if (-not $text.Contains($stamp)) {
    throw "The APK does not hold the code just built (build stamp $stamp is missing), so it is an old copy. Run 'flutter clean' in apps\mobile and try again. Nothing was copied to the phone."
}
if ($PosthogKey -and -not $text.Contains($PosthogKey)) {
    throw "The PostHog key is not inside the APK. Nothing was copied to the phone."
}
Write-Host "Checked: the APK holds the code built just now (build $stamp)."
if ($PosthogKey) { Write-Host "Checked: the PostHog key is inside the APK." }

Write-Host "Copying to the phone ..."
& $adb push $apk $remote
if ($LASTEXITCODE -ne 0) { throw "The copy failed." }

Write-Host ""
Write-Host "Done. Version $version, build $stamp. On the phone: Files > Downloads > priveo-dev-$version.apk > Install."
