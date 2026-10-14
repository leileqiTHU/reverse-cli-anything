# JSON-only wrapper. Pass CLI arguments unchanged to the local Python frontend.
$ErrorActionPreference = 'Stop'
$taskPython = $env:CAPCUT_PYTHON
$taskLocalSettings = Join-Path $PSScriptRoot 'local.settings.json'
if (-not $taskPython -and (Test-Path -LiteralPath $taskLocalSettings)) {
    $taskPython = (Get-Content -LiteralPath $taskLocalSettings -Raw | ConvertFrom-Json).python
}
if (-not $taskPython -or -not (Test-Path -LiteralPath $taskPython)) {
    . (Join-Path $PSScriptRoot '../tools/resolve-python.ps1')
    $taskPython = Resolve-ReverseCliPython -Repository (Split-Path $PSScriptRoot)
}
& $taskPython -B (Join-Path $PSScriptRoot 'capcut_agent.py') @args
exit $LASTEXITCODE
