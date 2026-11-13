#!/usr/bin/env pwsh
# ============================================================
# OrbisERP Script Runner
# Usage: .\run_script.ps1 <step_number>
# Example: .\run_script.ps1 1
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("1","2","3","4","5","6","7","8","9","10","11","12","13","14","14b","15","16","17","18","19","20","21","22","23","24","25","26","27","28","29","30","31","32","all")]
    [string]$Step,
    [switch]$Rollback,
    [switch]$Test
)

$CONTAINER = "frappe_docker-backend-1"
$SITE      = "frontend"

# Folder where this script lives (e:\Orbis-ERP\scripts)
$LOCAL_SCRIPTS = Split-Path -Parent $MyInvocation.MyCommand.Path

function Run-Step {
    param([string]$num)

    if ($num -eq "28" -and $Rollback -and $Test) {
        throw "Choose either -Rollback or -Test for step 28, not both."
    }

    $found = Get-ChildItem -Path $LOCAL_SCRIPTS -Filter "step${num}_*.py" | Select-Object -First 1
    if (-not $found) {
        Write-Host "ERROR: Could not find step${num}_*.py in $LOCAL_SCRIPTS" -ForegroundColor Red
        return
    }

    $localFile = $found.FullName
    $filename  = $found.Name

    Write-Host "`n>>> Copying $filename into container ..." -ForegroundColor Cyan
    docker cp $localFile "${CONTAINER}:/tmp/${filename}"

    if ($num -eq "27") {
        $dataFile = Join-Path $LOCAL_SCRIPTS "selling_demo_customers_and_quotations.json"
        if (-not (Test-Path -LiteralPath $dataFile)) {
            Write-Host "ERROR: Could not find Selling demo data file: $dataFile" -ForegroundColor Red
            return
        }
        Write-Host ">>> Copying Selling demo data into container ..." -ForegroundColor Cyan
        docker cp $dataFile "${CONTAINER}:/tmp/selling_demo_customers_and_quotations.json"
    }

    if ($num -eq "28") {
        docker cp $localFile "${CONTAINER}:/tmp/step18_simplify_manufacturing.py"
    }

    if ($num -eq "29") {
        docker cp $localFile "${CONTAINER}:/tmp/step19_hide_subcontracting.py"
    }

    Write-Host ">>> Running $filename inside ERPNext ..." -ForegroundColor Cyan

    $action = "run"
    if ($num -eq "28" -and $Rollback) { $action = "rollback" }
    if ($num -eq "28" -and $Test) { $action = "test_transactional_smoke" }
    if ($num -eq "26" -and $Rollback) { $action = "rollback" }
    if ($num -eq "29" -and $Rollback) { $action = "rollback" }
    if ($num -eq "31" -and $Rollback) { $action = "rollback" }
    if ($num -eq "32" -and $Rollback) { $action = "rollback" }

    $pyCode = @"
import sys
sys.path.insert(0, '/home/frappe/frappe-bench/apps/frappe')
sys.path.insert(0, '/home/frappe/frappe-bench/apps/erpnext')
sys.path.insert(0, '/tmp')
import frappe
frappe.init(site='$SITE', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
import importlib.util
spec = importlib.util.spec_from_file_location('step_script', '/tmp/$filename')
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
if '$action' == 'rollback':
    result = mod.rollback()
elif '$action' == 'test_transactional_smoke':
    result = mod.test_transactional_smoke()
elif hasattr(mod, 'run'):
    result = mod.run()
elif hasattr(mod, 'run_branding_setup'):
    result = mod.run_branding_setup()
elif hasattr(mod, 'setup_login_ui'):
    result = mod.setup_login_ui()
elif hasattr(mod, 'main'):
    result = mod.main()
else:
    result = 'Done'
frappe.db.commit()
print('RESULT:', result)
frappe.destroy()
"@

    docker exec -w /home/frappe/frappe-bench/sites $CONTAINER /home/frappe/frappe-bench/env/bin/python -c $pyCode
    if ($LASTEXITCODE -ne 0) {
        throw "$filename failed inside the Frappe container (exit $LASTEXITCODE)."
    }

    if ($num -eq "28" -and -not $Test) {
        Write-Host ">>> Restarting backend so server_script_enabled takes effect ..." -ForegroundColor Cyan
        docker restart $CONTAINER | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Could not restart $CONTAINER." }
    }

    Write-Host "`n>>> $filename execution finished." -ForegroundColor Green
}

if ($Step -eq "all") {
    foreach ($n in @("1","2","3","4","5","6","7","8","9","10","11","12","13","14","14b","15","16","17","18","19","20","21","22","23","24","25","26","27","28","29","30","31","32")) {
        Run-Step $n
    }
} else {
    Run-Step $Step
}
