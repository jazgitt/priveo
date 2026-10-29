<#
  A local PostgreSQL for development, optionally filled from the hosted test database.

    tools\dev\local-db.ps1             # start the local server; build the database on the first run
    tools\dev\local-db.ps1 -Refresh    # throw the local database away and build it again
    tools\dev\local-db.ps1 -Stop       # stop the local server

  The server listens on 127.0.0.1:5433 with no password and holds one database,
  `priveo`. Everything lives in the git-ignored folder `.local-db` at the repo
  root. Delete that folder to remove the copy and its data.

  - The schema is always built with the migrations. If services\api\.env has
    SOURCE_DATABASE_URL (the hosted test database, for example its Supabase session
    pooler address), the rows are copied across as a one-way snapshot
    (services\api\scripts\copy_dev_db.py); nothing is ever written to the hosted
    database, and it must be at the same migration as this code (the script says
    so if it is not). Without it you get an empty database with the schema: run
    services\api\scripts\seed.py for the logins.
  - It needs the PostgreSQL 17 tools. Set POSTGRES_BIN if they are not in
    C:\Program Files\PostgreSQL\17\bin.
  - SOURCE_DATABASE_URL is never printed. Vercel keeps the hosted values as sensitive
    variables, so it has to be put in services\api\.env by hand.
  - A copy holds the hosted test data. Keep it on this PC.
#>
param([switch]$Refresh, [switch]$Stop, [int]$Port = 5433)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$dir = Join-Path $root ".local-db"
$data = Join-Path $dir "data"
$bin = if ($env:POSTGRES_BIN) { $env:POSTGRES_BIN } else { "C:\Program Files\PostgreSQL\17\bin" }
$apiEnv = Join-Path $root "services\api\.env"
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
  $url = $null
  if (Test-Path $apiEnv) {
    foreach ($line in Get-Content $apiEnv) {
      if ($line -match '^\s*SOURCE_DATABASE_URL=(.*)$') { $url = $Matches[1].Trim().Trim('"') }
    }
  }
  $python = Join-Path $root "services\api\.venv\Scripts\python.exe"
  $api = Join-Path $root "services\api"

  # The hosted PostgreSQL can be newer than the local tools, so pg_dump would refuse.
  # Build the schema with the migrations, then stream the rows across.
  Run "psql" ($common + @("-d", "postgres", "-qc", "drop database if exists $db with (force)"))
  Run "createdb" ($common + @($db))
  $local = "postgresql://priveo@127.0.0.1:$Port/$db"
  Push-Location $api
  try {
    $env:DATABASE_URL = $local
    & $python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "alembic upgrade head failed" }
    if ($url) {
      Write-Host "Copying the hosted test database (read-only)..."
      $env:SOURCE_DATABASE_URL = $url
      $env:TARGET_DATABASE_URL = $local
      & $python scripts\copy_dev_db.py
      if ($LASTEXITCODE -ne 0) { throw "copy_dev_db.py failed" }
    } else {
      Write-Host "No SOURCE_DATABASE_URL in services\api\.env: empty database with the schema. Run scripts\seed.py for the logins."
    }
  } finally {
    Remove-Item Env:SOURCE_DATABASE_URL, Env:TARGET_DATABASE_URL, Env:DATABASE_URL -ErrorAction SilentlyContinue
    Pop-Location
  }
  $tables = & (Tool "psql") @common -d $db -tAc "select count(*) from information_schema.tables where table_schema='public'"
  $version = & (Tool "psql") @common -d $db -tAc "select version_num from alembic_version"
  Write-Host "Built: $tables tables, migration $version."
}

Write-Host "Local database ready: postgresql://priveo@127.0.0.1:$Port/$db"
