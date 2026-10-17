<#
  A local copy of the shared dev database (Neon), on a local PostgreSQL.

    tools\dev\local-db.ps1             # start the local server; copy from Neon on the first run
    tools\dev\local-db.ps1 -Refresh    # throw the local copy away and copy from Neon again
    tools\dev\local-db.ps1 -Stop       # stop the local server

  The server listens on 127.0.0.1:5433 with no password and holds one database,
  `priveo`. Everything lives in the git-ignored folder `.local-db` at the repo
  root. Delete that folder to remove the copy and its data.

  - The copy is a one-way snapshot (services\api\scripts\copy_dev_db.py). Nothing is
    ever written to Neon. It builds the schema with the migrations, so Neon must be
    at the same migration as this code (the script says so if it is not).
  - It needs the PostgreSQL 17 tools. Set POSTGRES_BIN if they are not in
    C:\Program Files\PostgreSQL\17\bin.
  - The Neon address comes from services\api\.env.neon, which portal-local.ps1
    pulls from Vercel. It is never printed.
  - The copy holds the real dev customer data. Keep it on this PC.
#>
param([switch]$Refresh, [switch]$Stop, [int]$Port = 5433)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$dir = Join-Path $root ".local-db"
$data = Join-Path $dir "data"
$bin = if ($env:POSTGRES_BIN) { $env:POSTGRES_BIN } else { "C:\Program Files\PostgreSQL\17\bin" }
$neonEnv = Join-Path $root "services\api\.env.neon"
$db = "priveo"
$common = @("-h", "127.0.0.1", "-p", "$Port", "-U", "priveo")

function Tool($name) { Join-Path $bin "$name.exe" }
function Run($name, [string[]]$tail) {
  & (Tool $name) @tail
  if ($LASTEXITCODE -ne 0) { throw "$name failed (exit $LASTEXITCODE)" }
}
function Is-Running {
  & (Tool "pg_ctl") -D $data status *> $null
  return ($LASTEXITCODE -eq 0)
}

if (-not (Test-Path (Tool "initdb"))) { throw "PostgreSQL tools not found in $bin. Set POSTGRES_BIN." }

if ($Stop) {
  if (Test-Path $data) { if (Is-Running) { Run "pg_ctl" @("-D", $data, "-m", "fast", "-w", "stop") } }
  Write-Host "Local database stopped."
  return
}

New-Item -ItemType Directory -Force $dir | Out-Null
if (-not (Test-Path (Join-Path $data "PG_VERSION"))) {
  Write-Host "Creating the local PostgreSQL cluster..."
  Run "initdb" @("-D", $data, "-A", "trust", "-U", "priveo", "--encoding=UTF8", "--locale=C")
}
if (-not (Is-Running)) {
  Write-Host "Starting the local database on port $Port..."
  Run "pg_ctl" @("-D", $data, "-l", (Join-Path $dir "server.log"), "-o", "-h 127.0.0.1 -p $Port", "-w", "start")
}

$exists = (& (Tool "psql") @common -d postgres -tAc "select 1 from pg_database where datname='$db'") -eq "1"
if ($Refresh -or -not $exists) {
  if (-not (Test-Path $neonEnv)) {
    throw "services\api\.env.neon is missing. Run tools\dev\portal-local.ps1 -Refresh once to pull it."
  }
  $url = $null
  foreach ($line in Get-Content $neonEnv) {
    if ($line -match '^\s*DATABASE_URL=(.*)$') { $url = $Matches[1].Trim().Trim('"') }
  }
  if (-not $url) { throw "DATABASE_URL is missing from .env.neon" }
  $python = Join-Path $root "services\api\.venv\Scripts\python.exe"
  $api = Join-Path $root "services\api"

  # Neon runs a newer PostgreSQL than the local tools, so pg_dump would refuse.
  # Build the schema with the migrations, then stream the rows across.
  Run "psql" ($common + @("-d", "postgres", "-qc", "drop database if exists $db with (force)"))
  Run "createdb" ($common + @($db))
  $local = "postgresql://priveo@127.0.0.1:$Port/$db"
  Push-Location $api
  try {
    $env:DATABASE_URL = $local
    & $python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "alembic upgrade head failed" }
    Write-Host "Copying the dev database from Neon (read-only)..."
    $env:SOURCE_DATABASE_URL = $url
    $env:TARGET_DATABASE_URL = $local
    & $python scripts\copy_dev_db.py
    if ($LASTEXITCODE -ne 0) { throw "copy_dev_db.py failed" }
  } finally {
    Remove-Item Env:SOURCE_DATABASE_URL, Env:TARGET_DATABASE_URL, Env:DATABASE_URL -ErrorAction SilentlyContinue
    Pop-Location
  }
  $tables = & (Tool "psql") @common -d $db -tAc "select count(*) from information_schema.tables where table_schema='public'"
  $version = & (Tool "psql") @common -d $db -tAc "select version_num from alembic_version"
  Write-Host "Copied: $tables tables, migration $version."
}

Write-Host "Local database ready: postgresql://priveo@127.0.0.1:$Port/$db"
