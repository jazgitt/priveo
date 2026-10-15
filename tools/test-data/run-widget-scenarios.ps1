<#
.SYNOPSIS
  Runs the scenario widget tests (apps/mobile/test/scenarios) on this PC.

.DESCRIPTION
  Builds a fresh disposable fixture database, starts the isolated fixture API
  on it, runs the real app screens against that API with `flutter test`, and
  stops the API. No emulator, phone or hosted database is involved. Nothing
  here touches DATABASE_URL or .local/test-data/manual.sqlite3.

  Passwords are throw-away values for the disposable database.
#>
param(
    [int]$Port = 8011,
    # Pass a test name fragment to run a subset, for example "C20".
    [string]$Name = ''
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$apiRoot = Join-Path $repoRoot 'services/api'
$work = Join-Path $repoRoot '.local/widget'
$pythonExe = if ($env:E2E_PYTHON) { $env:E2E_PYTHON } else { Join-Path $apiRoot '.venv/Scripts/python.exe' }
New-Item -ItemType Directory -Force $work | Out-Null
$db = Join-Path $work 'w.sqlite3'
$manifest = Join-Path $work 'manifest.json'
foreach ($f in @($db, $manifest)) { if (Test-Path $f) { Remove-Item $f -Force } }

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

$shell = if (Get-Command pwsh -ErrorAction SilentlyContinue) { 'pwsh' } else { 'powershell' }
$log = Join-Path $work 'api.log'
$api = Start-Process $shell -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $log -RedirectStandardError (Join-Path $work 'api.err') `
    -ArgumentList '-NoProfile', '-File', (Join-Path $PSScriptRoot 'start-api.ps1'),
        '-DatabaseFile', $db, '-Port', $Port, '-SerializeRequests'
try {
    $ready = $false
    for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
        try {
            $null = Invoke-WebRequest "http://127.0.0.1:$Port/openapi.json" -UseBasicParsing -TimeoutSec 2
            $ready = $true
        } catch { Start-Sleep 2 }
    }
    if (-not $ready) { throw "The fixture API did not start. See $log" }

    Push-Location (Join-Path $repoRoot 'apps/mobile')
    try {
        $args = @(
            'test', 'test/scenarios',
            "--dart-define=SCENARIO_API_URL=http://127.0.0.1:$Port",
            "--dart-define=SCENARIO_MANIFEST_FILE=$manifest",
            "--dart-define=SCENARIO_PASSWORD=$customerPassword",
            "--dart-define=SCENARIO_ADMIN_PASSWORD=$adminPassword"
        )
        if ($Name) { $args += @('--plain-name', $Name) }
        & flutter @args
        $code = $LASTEXITCODE
    } finally { Pop-Location }
} finally {
    # Stop the launcher and the API it started.
    Get-CimInstance Win32_Process |
        Where-Object { $_.ProcessId -eq $api.Id -or $_.ParentProcessId -eq $api.Id } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
exit $code
