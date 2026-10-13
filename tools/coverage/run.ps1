param([switch]$SkipStaticChecks)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pythonRunner = Join-Path $taskRoot 'services\api\.venv\Scripts\python.exe'
$previousDatabase = $env:TEST_DATABASE_URL
try {
    # Coverage uses a disposable in-memory database, never a developer database.
    $env:TEST_DATABASE_URL = 'sqlite://'
    Push-Location (Join-Path $taskRoot 'services\api')
    try {
        & $pythonRunner -m coverage run --branch --source=app -m pytest -q --basetemp=.pytest-tmp-coverage
        if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
        & $pythonRunner -m coverage json -o coverage-final.json
        if ($LASTEXITCODE -ne 0) { throw 'Backend coverage export failed.' }
    } finally { Pop-Location }
    Push-Location (Join-Path $taskRoot 'apps\mobile')
    try {
        & flutter test --coverage --coverage-path=coverage/final-lcov.info --coverage-package=priveo
        if ($LASTEXITCODE -ne 0) { throw 'Mobile tests failed.' }
        if (-not $SkipStaticChecks) {
            & flutter analyze
            if ($LASTEXITCODE -ne 0) { throw 'Mobile analysis failed.' }
        }
    } finally { Pop-Location }
    Push-Location (Join-Path $taskRoot 'apps\web')
    try {
        & npm run test:coverage
        if ($LASTEXITCODE -ne 0) { throw 'Web coverage failed.' }
        if (-not $SkipStaticChecks) {
            & npm run build
            if ($LASTEXITCODE -ne 0) { throw 'Web build failed.' }
        }
    } finally { Pop-Location }
    Push-Location $taskRoot
    try {
        & $pythonRunner tools/coverage/report.py
        if ($LASTEXITCODE -ne 0) { throw 'An application area is below 90% line coverage or has unmeasured source.' }
    } finally { Pop-Location }
} finally {
    if ($null -eq $previousDatabase) { Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue }
    else { $env:TEST_DATABASE_URL = $previousDatabase }
}
