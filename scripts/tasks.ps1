param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('run-api', 'run-ui', 'test')]
    [string]$Task
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    switch ($Task) {
        'run-api' { python -m uvicorn medsafe.api.app:app --reload }
        'run-ui' { python -m streamlit run ui/app.py }
        'test' { python -m pytest -q }
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
