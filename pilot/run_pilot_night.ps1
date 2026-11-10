# Pilot night (task B5, owner B) - Mon 9 Nov. Run on the FINAL-RUN machine, from the repo folder:
#     powershell -ExecutionPolicy Bypass -File pilot\run_pilot_night.ps1
# Steps: licence check -> git pull -> tests -> generate/validate candidates -> preview -> pilot runs (30 s + 30 s)
#        -> verify every saved solution -> preliminary classes + SELECTION.md draft.
# Safe to stop and restart: the runner resumes from the first missing (instance, method) row.
$ErrorActionPreference = "Continue"     # decide on exit codes below; warnings printed by Python must not abort the night
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$log = "results\pilot_night.log"
New-Item -ItemType Directory -Force results | Out-Null
function Step($name) { $line = "`n=== $(Get-Date -Format 'HH:mm:ss')  $name"; Write-Host $line; Add-Content $log $line }

Step "1/7 Gurobi licence check (a model above the free 2,000-variable limit)"
& $py -c "import gurobipy as gp; m=gp.Model(); m.Params.LogToConsole=0; x=m.addVars(5000, obj=1.0); m.addConstrs(x[i]>=1 for i in range(5000)); m.optimize(); print('licence OK')"
if ($LASTEXITCODE -ne 0) { Write-Host "STOP: no full Gurobi licence on this machine (free version limited to 2,000 variables)."; exit 1 }

Step "2/7 git pull"
$git = (Get-Command git -ErrorAction SilentlyContinue).Source            # Git on PATH, else its standard location
if (-not $git) { $git = "C:\Program Files\Git\cmd\git.exe" }
& $git pull --ff-only
if ($LASTEXITCODE -ne 0) { Write-Host "STOP: git pull failed - resolve it first."; exit 1 }

Step "3/7 test suite (never start a night on red tests)"
& $py -m pytest -q -p no:cacheprovider tests/
if ($LASTEXITCODE -ne 0) { Write-Host "STOP: tests failed."; exit 1 }

Step "4/7 generate + validate the candidate instances"
& $py -m pilot.run_pilot --grid pilot/grid.json --generate-only
Step "5/7 preview: density, |A|, |P|, SP buildability (no solver)"
& $py -m pilot.preview --out results/pilot_preview.csv

Step "6/7 PILOT RUNS: AF, AF+S, SP, SP+S at 30 s + 30 s (worst case about 1.6 h)"
& $py -m pilot.run_pilot --grid pilot/grid.json --out results/pilot.csv

Step "7/7 verify solutions + preliminary classes"
& $py -m qa.verify_results results/pilot.csv --manifest none --instances instances/candidates
& $py -m pilot.classify --runs results/pilot.csv --stage pilot --out results/SELECTION_pilot.md `
    --classes-csv results/pilot_classes.csv --candidates-csv results/confirm_candidates.csv
Step "DONE. Tuesday (B6): check results/SELECTION_pilot.md; give results/confirm_candidates.csv to C for the confirmation runs (plain AF and SP at the final limits)."
