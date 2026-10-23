$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Invoke-DagRun([string]$Suffix) {
    $runId = 'verify_' + $Suffix + '_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
    docker compose exec -T airflow-scheduler airflow dags unpause agri_prices_etl
    if ($LASTEXITCODE -ne 0) { throw 'DAG unpause failed.' }
    docker compose exec -T airflow-scheduler airflow dags trigger agri_prices_etl --run-id $runId
    if ($LASTEXITCODE -ne 0) { throw 'DAG trigger failed.' }
    for ($i = 0; $i -lt 240; $i++) {
        $state = docker compose exec -T airflow-scheduler python /opt/airflow/scripts/run_state.py $runId
        if ($LASTEXITCODE -ne 0) { throw 'Could not query DAG state.' }
        $last = ($state | Select-Object -Last 1).Trim()
        if ($last -eq 'success') { return $runId }
        if ($last -eq 'failed') { throw "DAG $runId failed. Inspect Airflow task logs." }
        Start-Sleep -Seconds 5
    }
    throw "Timed out waiting for $runId"
}
$first = Invoke-DagRun 'first'
$before = docker compose exec -T airflow-scheduler python /opt/airflow/scripts/db_summary.py --count-only
if ($LASTEXITCODE -ne 0) { throw 'Database count query failed.' }
$second = Invoke-DagRun 'repeat'
$after = docker compose exec -T airflow-scheduler python /opt/airflow/scripts/db_summary.py --count-only
if ($LASTEXITCODE -ne 0) { throw 'Database count query failed.' }
Write-Host "DAGs succeeded: $first / $second"
Write-Host "Rows before: $before ; after: $after"
docker compose exec -T airflow-scheduler python /opt/airflow/scripts/verify_db.py
if ($LASTEXITCODE -ne 0) { throw 'UPSERT verification failed.' }
if ([int]$before -ne [int]$after) { Write-Warning 'Counts changed: check for new live observations before concluding that UPSERT failed.' }
Write-Host 'Capture actual Graph/Grid/Dashboard views. Existing real-data replay and DQ tests: scripts/integration_check.py (isolated empty DB only).'
