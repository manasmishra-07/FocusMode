param(
    [ValidateSet('server','client','agent','check','setup')]
    [string]$Component = 'check',
    [switch]$Real
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Create the environment first: python -m venv .venv'
}
switch ($Component) {
    'setup' {
        & $projectPython -m pip install -r server\requirements.txt -r agent\requirements.txt
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        foreach ($folder in @('server','client','agent')) {
            if (-not (Test-Path -LiteralPath "$folder\.env")) {
                Copy-Item -LiteralPath "$folder\.env.example" -Destination "$folder\.env"
            }
        }
        & $projectPython server\manage.py migrate
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Push-Location client
        try { npm.cmd install } finally { Pop-Location }
    }
    'server' { & $projectPython server\manage.py runserver 127.0.0.1:8000 }
    'client' {
        Push-Location client
        try { npm.cmd run dev } finally { Pop-Location }
    }
    'agent' {
        $selectedAdapter = if ($Real) { 'windows' } else { 'mock' }
        & $projectPython agent\main.py --adapter $selectedAdapter
    }
    'check' {
        & $projectPython server\manage.py check
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $projectPython server\manage.py migrate --check
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host 'Backend configuration and migrations are ready.'
        Write-Host 'Use three terminals: .\run.ps1 server / .\run.ps1 client / .\run.ps1 agent'
        Write-Host 'Agent defaults to simulation. For real confirmed Windows focus: .\run.ps1 agent -Real'
    }
}
exit $LASTEXITCODE
