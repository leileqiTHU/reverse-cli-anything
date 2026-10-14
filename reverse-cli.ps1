$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'tools/resolve-python.ps1')
$taskPython = Resolve-ReverseCliPython -Repository $PSScriptRoot
& $taskPython -B (Join-Path $PSScriptRoot 'reverse-cli.py') @args
exit $LASTEXITCODE
