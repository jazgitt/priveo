<#
  Run the admin portal on localhost against the dev Neon database.

    tools\dev\portal-local.ps1            # API on :8000 and portal on :5173
    tools\dev\portal-local.ps1 -Refresh   # pull the Vercel env again first
    tools\dev\portal-local.ps1 -ApiOnly   # API only (no portal dev server)
    tools\dev\portal-local.ps1 -Local     # use the local copy of the database instead of Neon

  Open http://localhost:5173/portal/ and sign in as usual.

  - The database is the shared dev Neon database. There is no local copy, so
    what you save here is real dev data.
  - The Vercel env is pulled once into services\api\.env.neon (git-ignored, never
    printed). Use -Refresh after a variable changes on Vercel.
  - This does not run migrations or the seed. The deploy does that. If you add a
    migration, apply it first with:  .venv\Scripts\python -m alembic upgrade head
    from services\api, with the same env loaded.
  - With -Local the API uses the local copy made by tools\dev\local-db.ps1
    (127.0.0.1:5433), starting it if needed. Nothing reaches Neon. Email, push and
    S3 are switched off so a test cannot message a real customer. Local migrations
    (alembic upgrade head) are applied to the copy at start-up. Refresh the copy
    with tools\dev\local-db.ps1 -Refresh.
  - The portal dev server (Vite) reloads on every edit and proxies /v1 to the API.
    The API reloads on Python edits.
#>
param([switch]$Refresh, [switch]$ApiOnly, [switch]$Local, [int]$ApiPort = 8000)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$api = Join-Path $root "services\api"
$web = Join-Path $root "apps\web"
$envFile = Join-Path $api ".env.neon"

if ($Refresh -or -not (Test-Path $envFile)) {
  Write-Host "Pulling the dev environment from Vercel..."
  Push-Location $api
  try { npx vercel env pull ".env.neon" --environment production --yes | Out-Null } finally { Pop-Location }
  if (-not (Test-Path $envFile)) { throw "vercel env pull did not write .env.neon" }
}

# Load KEY=VALUE lines into this process (values are never echoed).
foreach ($line in Get-Content $envFile) {
  if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
    $v = $Matches[2].Trim()
    if ($v.Length -ge 2 -and $v.StartsWith('"') -and $v.EndsWith('"')) { $v = $v.Substring(1, $v.Length - 2) }
    Set-Item -Path "Env:$($Matches[1])" -Value $v
  }
}
if (-not $env:DATABASE_URL) { throw "DATABASE_URL is missing from .env.neon" }
if ($Local) {
  & (Join-Path $PSScriptRoot "local-db.ps1")
  if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) { throw "local-db.ps1 failed" }
  $env:DATABASE_URL = "postgresql://priveo@127.0.0.1:5433/priveo"
  # Nothing may leave this PC: no real email, push or object storage.
  foreach ($k in "RESEND_API_KEY", "EMAIL_REDIRECT_TO", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET") {
    Set-Item -Path "Env:$k" -Value ""
  }
  $env:FCM_ENABLED = "false"
  $env:MEDIA_STORE = "local"
  Push-Location $api
  try { & (Join-Path $api ".venv\Scripts\python.exe") -m alembic upgrade head } finally { Pop-Location }
}
# Plain http on localhost: the API must not insist on Secure cookies or the prod rules.
$env:ENVIRONMENT = "dev"
$env:PUBLIC_BASE_URL = "http://localhost:5173"

$python = Join-Path $api ".venv\Scripts\python.exe"
$apiArgs = @("-m", "uvicorn", "app.main:app", "--reload", "--port", "$ApiPort")

if ($ApiOnly) {
  Push-Location $api; try { & $python @apiArgs } finally { Pop-Location }
  return
}

# The API runs as a child process (it inherits the env above); its log goes to
# the API folder, file .local-api.log. Ctrl+C in this window stops both.
$log = Join-Path $api ".local-api.log"
$proc = Start-Process -FilePath $python -ArgumentList $apiArgs -WorkingDirectory $api `
  -RedirectStandardOutput $log -RedirectStandardError "$log.err" -PassThru -WindowStyle Hidden
try {
  Write-Host "API on http://localhost:$ApiPort (log: the API folder, file .local-api.log). Portal: http://localhost:5173/portal/"
  $env:VITE_API_TARGET = "http://localhost:$ApiPort"
  Push-Location $web
  try { npm run dev } finally { Pop-Location }
} finally {
  if (-not $proc.HasExited) { taskkill /PID $proc.Id /T /F | Out-Null }
}
