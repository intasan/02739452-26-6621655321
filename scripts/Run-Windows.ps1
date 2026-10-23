$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Install Docker Desktop and enable Linux containers first.' }
docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Open Docker Desktop, wait until the engine is running, then retry.' }
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    $lines = Get-Content '.env'
    function New-LocalSecret {
        $bytes = New-Object byte[] 24
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        return [BitConverter]::ToString($bytes).Replace('-', '')
    }
    $dbSecret = New-LocalSecret
    $adminSecret = New-LocalSecret
    $lines = $lines -replace '^POSTGRES_PASSWORD=.*$', "POSTGRES_PASSWORD=$dbSecret"
    $lines = $lines -replace '^AIRFLOW_ADMIN_PASSWORD=.*$', "AIRFLOW_ADMIN_PASSWORD=$adminSecret"
    [System.IO.File]::WriteAllLines((Join-Path (Get-Location) '.env'), $lines, (New-Object System.Text.UTF8Encoding $false))
    Write-Host 'Created private .env with random passwords; do not commit this file.'
}
if ((Get-Content '.env' -Raw) -match 'replace_with|change_me') { throw 'Replace placeholder passwords in .env before continuing.' }
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed.' }
docker compose up -d --wait postgres
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL did not become healthy.' }
docker compose up --no-deps --abort-on-container-exit --exit-code-from airflow-init airflow-init
if ($LASTEXITCODE -ne 0) { throw 'Airflow initialization failed. Inspect the logs above.' }
docker compose up -d airflow-scheduler airflow-webserver dashboard
if ($LASTEXITCODE -ne 0) { throw 'Service startup failed.' }
docker compose ps
Write-Host 'Airflow: http://localhost:8080 (admin; password in .env)'
Write-Host 'Dashboard: http://localhost:8501'
Write-Host 'Wait for Airflow webserver readiness, then run scripts/Verify-Windows.ps1.'
