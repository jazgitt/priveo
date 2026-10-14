param(
    [Parameter(Mandatory = $true)][string]$DatabaseFile,
    [int]$Port = 8000,
    # One request thread: needed when a browser drives the SQLite fixture API.
    [switch]$SerializeRequests
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$apiRoot = Join-Path $repoRoot 'services/api'
# E2E_PYTHON lets CI (Linux, no .venv) name its interpreter.
$pythonExe = if ($env:E2E_PYTHON) { $env:E2E_PYTHON } else { Join-Path $apiRoot '.venv/Scripts/python.exe' }
$databasePath = (Resolve-Path -LiteralPath $DatabaseFile).Path
$databaseUrl = 'sqlite:///' + $databasePath.Replace('\', '/')
$mediaRoot = Join-Path (Split-Path -Parent $databasePath) 'media'
$overrides = @{
    DATABASE_URL = $databaseUrl
    ENVIRONMENT = 'dev'
    RESEND_API_KEY = ''
    TOKEN_SECRET = 'local-fixture-only-secret-not-for-deployment'
    MOCK_EMAIL_CODE = '246810'
    MEDIA_ROOT = $mediaRoot
    MONEY_GST_CONFIGURATION_MOCK = 'true'
    MONEY_UPI_ID = 'priveo-placeholder@upi'
    MONEY_UPI_PAYEE_NAME = 'Priveo (test placeholder)'
    MONEY_UPI_QR_URL = ''
    MONEY_SELLER_NAME = 'Priveo (placeholder seller)'
    MONEY_SELLER_ADDRESS = 'Placeholder address'
    MONEY_SELLER_GSTIN = '00PLACEHOLDER0Z0'
    MONEY_GST_RATE_PERCENT = '18'
    MONEY_GST_MODE = 'CGST_SGST'
}
$previous = @{}
foreach ($key in $overrides.Keys) {
    $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
    [Environment]::SetEnvironmentVariable($key, $overrides[$key], 'Process')
}
$previousLocation = Get-Location
try {
    Set-Location -LiteralPath $apiRoot
    # Refuse to start against a database this fixture tool has not initialized.
    & $pythonExe scripts/test_data.py --database-file $databasePath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Test database verification failed.' }
    Write-Host "Test API: http://127.0.0.1:$Port (phone: use this computer's LAN address)"
    Write-Host 'This process uses the dedicated test database and logging email sender.'
    if ($SerializeRequests) {
        $toolDir = Join-Path $repoRoot 'tools/test-data'
        & $pythonExe -m uvicorn serial_app:app --app-dir $toolDir --host 0.0.0.0 --port $Port
    } else {
        & $pythonExe -m uvicorn app.main:app --host 0.0.0.0 --port $Port
    }
    if ($LASTEXITCODE -ne 0) { throw 'Test API exited with an error.' }
}
finally {
    Set-Location -LiteralPath $previousLocation
    foreach ($key in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process')
    }
}
