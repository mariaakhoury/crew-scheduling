# Benchmark selection + freeze (tasks B16 + B9, owner B) - Wed 11 Nov, after C's confirmation runs (C15).
# Run from the repo folder:
#     powershell -ExecutionPolicy Bypass -File pilot\select_and_freeze.ps1
# Steps: pull -> check results/confirm.csv (one machine, one configuration, every candidate x AF/SP present)
#        -> verify every saved solution -> classify (confirmation rows + stable pilot classes) -> select with the
#        written rule (issue #1) -> check the minimums -> freeze to instances/final (+ MANIFEST.csv, README.md)
#        -> tests. Stops at the first problem. Commits NOTHING: review instances/final/SELECTION.md, then push.
param([switch]$SkipPull)
$ErrorActionPreference = "Continue"     # decide on exit codes; warnings printed by Python must not abort
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$git = (Get-Command git -ErrorAction SilentlyContinue).Source            # Git on PATH, else its standard location
if (-not $git) { $git = "C:\Program Files\Git\cmd\git.exe" }
if (-not (Test-Path $git)) { Write-Host "STOP: Git not found." -ForegroundColor Red; exit 1 }
function Step($name) { Write-Host "`n=== $(Get-Date -Format 'HH:mm:ss')  $name" }
function Stop-Here($why) { Write-Host "`nSTOP: $why" -ForegroundColor Red; exit 1 }

if (-not $SkipPull) {
    Step "1/8 git pull (C pushes results/confirm.csv)"
    & $git pull --ff-only
    if ($LASTEXITCODE -ne 0) { Stop-Here "git pull failed - resolve it first." }
}
if (-not (Test-Path "results/confirm.csv")) { Stop-Here "results/confirm.csv not found - has C pushed the confirmation runs?" }

Step "2/8 confirmation data: one machine, one configuration, every candidate x {AF, SP}"
& $py -c @"
import sys; sys.path.insert(0, '.')
import pandas as pd
from crew.analysis import load_runs
try:
    df = load_runs('results/confirm.csv')          # refuses stale rows, mixed machines, mixed configurations
except ValueError as exc:
    sys.exit(f'confirm.csv rejected: {exc}')
cand = pd.read_csv('results/confirm_candidates.csv')['instance']
have = set(zip(df['instance'], df['method']))
missing = [(i, m) for i in cand for m in ('AF', 'SP') if (i, m) not in have]
if missing:
    sys.exit(f'{len(missing)} candidate runs missing in confirm.csv, e.g. {missing[:4]}')
bad = df[df['status'].isin(['ERROR', 'CHECK_FAILED', 'INFEASIBLE', 'INF_OR_UNBD'])]
if len(bad):
    sys.exit(f'{len(bad)} rows need a rerun first: ' + ', '.join(bad['instance'] + '/' + bad['method'] + ':' + bad['status']))
print(f'OK: {len(df)} rows, machine {df.machine_id.iloc[0]}, configuration {str(df.config_hash.iloc[0])[:12]}, '
      f'time limit {df.time_limit_s.iloc[0]} s')
"@
if ($LASTEXITCODE -ne 0) { Stop-Here "confirmation data not usable (see the message above)." }

Step "3/8 verify every confirmation solution (checker, Q13/Q23)"
& $py -m qa.verify_results results/confirm.csv --manifest none --instances instances/candidates --report results/B8_confirm_report.md
if ($LASTEXITCODE -ne 0) { Stop-Here "verify_results found problems (results/B8_confirm_report.md)." }

Step "4/8 classify + select (confirmation classes win; EASY / both-optimal MEDIUM keep their pilot class)"
New-Item -ItemType Directory -Force instances/final | Out-Null
& $py -m pilot.classify --runs results/confirm.csv --pilot results/pilot.csv results/pilot_small.csv --stage confirm `
    --out instances/final/SELECTION.md --classes-csv results/final_classes.csv --selected-csv results/selected.csv
if ($LASTEXITCODE -ne 0) { Stop-Here "classify failed." }

Step "5/8 check the minimums (professor: >= 15, easy to very hard; plan: >= 3 time limit, >= 2 SP_not_built)"
& $py -c @"
import sys; import pandas as pd
s = pd.read_csv('results/selected.csv')
problems = []
if len(s) < 15: problems.append(f'only {len(s)} instances selected (< 15)')
if int(s['SP_not_built'].astype(bool).sum()) < 2: problems.append('fewer than 2 SP_not_built instances')
if int((s['class'] == 'TIME_LIMIT').sum()) < 3: problems.append('fewer than 3 TIME_LIMIT instances')
if int((s['class'] == 'EASY').sum()) < 1: problems.append('no EASY instance (professor: instances every model solves quickly)')
if s['class'].isin(['UNCONFIRMED', 'NOT_BUILT', 'UNUSABLE']).any(): problems.append('an unselectable class was selected (bug)')
print(s['class'].value_counts().to_string()); print(f'total {len(s)}, n {s.n.min()}-{s.n.max()}, SP_not_built {int(s.SP_not_built.astype(bool).sum())}')
sys.exit('; '.join(problems)) if problems else print('OK: all minimums met')
"@
if ($LASTEXITCODE -ne 0) { Stop-Here "selection does not meet a minimum (see above) - discuss with the group before freezing." }

Step "6/8 freeze: copy the selected files to instances/final, write MANIFEST.csv + README.md"
& $py -m pilot.freeze --selection results/selected.csv --from instances/candidates --to instances/final
if ($LASTEXITCODE -ne 0) { Stop-Here "freeze failed." }

Step "7/8 check the frozen benchmark (fingerprints, files, documentation)"
& $py -c @"
import sys, os; sys.path.insert(0, '.')
import pandas as pd
from crew.version import file_sha256
from crew.instance import load_instance
m = pd.read_csv('instances/final/MANIFEST.csv')
bad = [r['name'] for _, r in m.iterrows() if file_sha256(os.path.join('instances/final', r['file'])) != r['sha256']]
for f in m['file']: load_instance(os.path.join('instances/final', f))      # V1-V10 again
if bad: sys.exit(f'fingerprint mismatch: {bad}')
for f in ('SELECTION.md', 'README.md', 'MANIFEST.csv'):
    if not os.path.exists(os.path.join('instances/final', f)): sys.exit(f'missing instances/final/{f}')
print(f'OK: {len(m)} frozen instances, fingerprints match, documentation present')
"@
if ($LASTEXITCODE -ne 0) { Stop-Here "frozen benchmark check failed." }

Step "8/8 test suite"
& $py -m pytest -q -p no:cacheprovider tests/
if ($LASTEXITCODE -ne 0) { Stop-Here "tests failed - do not push." }

Step "DONE. Review instances/final/SELECTION.md (class mix, fill-up note), then commit + push:"
Write-Host "  instances/final/ (files + MANIFEST.csv + README.md + SELECTION.md), results/selected.csv,"
Write-Host "  results/final_classes.csv, results/B8_confirm_report.md. Then Gate 2: all three approve; C tags v1.0-final-run."
