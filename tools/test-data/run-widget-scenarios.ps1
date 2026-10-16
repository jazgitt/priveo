<#
.SYNOPSIS
  Runs the scenario widget tests (apps/mobile/test/scenarios) on this PC.

.DESCRIPTION
  Builds a fresh disposable fixture database once, then runs each test file
  against its own copy of it: the isolated fixture API is stopped, the pristine
  copy is put back, and the API is started again before every file. Tests in
  different files change the same records (a paid bill, a read notification),
  so they must not share a database. Within one file the tests run in order.
  No emulator, phone or hosted database is involved. Nothing here touches
  DATABASE_URL or .local/test-data/manual.sqlite3.

  Passwords are throw-away values for the disposable database.
#>
param(
    [int]$Port = 8011,
    # Pass a test name fragment to run a subset, for example "C20".
    [string]$Name = '',
    # A test file or folder under apps/mobile, for example test/scenarios/scenario_crew_test.dart.
    [string]$Path = 'test/scenarios'
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$apiRoot = Join-Path $repoRoot 'services/api'
$mobileRoot = Join-Path $repoRoot 'apps/mobile'
$work = Join-Path $repoRoot '.local/widget'
$pythonExe = if ($env:E2E_PYTHON) { $env:E2E_PYTHON } else { Join-Path $apiRoot '.venv/Scripts/python.exe' }
New-Item -ItemType Directory -Force $work | Out-Null
$db = Join-Path $work 'w.sqlite3'
$pristine = Join-Path $work 'w.pristine.sqlite3'
$manifest = Join-Path $work 'manifest.json'
foreach ($f in @($db, $pristine, $manifest)) { if (Test-Path $f) { Remove-Item $f -Force } }

$customerPassword = 'PriveoWidget123!'
$adminPassword = 'PriveoWidgetAdmin123!'
$env:ENVIRONMENT = 'dev'
$env:TEST_DATA_PASSWORD = $customerPassword
$env:TEST_DATA_ADMIN_PASSWORD = $adminPassword
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue

Push-Location $apiRoot
try {
    & $pythonExe scripts/test_data.py --database-file $db --init --refresh all --output $manifest | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not build the fixture database.' }
} finally { Pop-Location }
Copy-Item $db $pristine

$shell = if (Get-Command pwsh -ErrorAction SilentlyContinue) { 'pwsh' } else { 'powershell' }
$log = Join-Path $work 'api.log'
$script:api = $null

function Stop-FixtureApi {
    if ($script:api) {
        Get-CimInstance Win32_Process |
            Where-Object { $_.ProcessId -eq $script:api.Id -or $_.ParentProcessId -eq $script:api.Id } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        $script:api = $null
    }
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

function Start-FixtureApi {
    $script:api = Start-Process $shell -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $log -RedirectStandardError (Join-Path $work 'api.err') `
        -ArgumentList '-NoProfile', '-File', (Join-Path $PSScriptRoot 'start-api.ps1'),
            '-DatabaseFile', $db, '-Port', $Port, '-SerializeRequests'
    for ($i = 0; $i -lt 60; $i++) {
        try {
            $null = Invoke-WebRequest "http://127.0.0.1:$Port/openapi.json" -UseBasicParsing -TimeoutSec 2
            return
        } catch { Start-Sleep -Seconds 2 }
    }
    throw "The fixture API did not start. See $log"
}

# The files to run: the one named, or every scenario_*_test.dart in a folder.
$target = Join-Path $mobileRoot $Path
$files = if (Test-Path $target -PathType Container) {
    Get-ChildItem $target -Filter 'scenario_*_test.dart' | Sort-Object Name |
        ForEach-Object { "$Path/$($_.Name)" }
} else { @($Path) }

$failed = @()
try {
    foreach ($file in $files) {
        Stop-FixtureApi
        Copy-Item $pristine $db -Force
        Start-FixtureApi

        Push-Location $mobileRoot
        try {
            $testArgs = @(
                'test', $file,
                "--dart-define=SCENARIO_API_URL=http://127.0.0.1:$Port",
                "--dart-define=SCENARIO_MANIFEST_FILE=$manifest",
                "--dart-define=SCENARIO_PASSWORD=$customerPassword",
                "--dart-define=SCENARIO_ADMIN_PASSWORD=$adminPassword"
            )
            if ($Name) { $testArgs += @('--plain-name', $Name) }
            & flutter @testArgs
            if ($LASTEXITCODE -ne 0) { $failed += $file }
        } finally { Pop-Location }
    }
} finally {
    Stop-FixtureApi
}
if ($failed.Count -gt 0) {
    Write-Host "FAILED FILES: $($failed -join ', ')"
    exit 1
}
Write-Host "All $($files.Count) scenario test file(s) passed."
exit 0
