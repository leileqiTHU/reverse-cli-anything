$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../tools/resolve-python.ps1')
$python=Resolve-ReverseCliPython -Repository (Split-Path $PSScriptRoot)
$env:PYTHONIOENCODING='utf-8'
& $python (Join-Path $PSScriptRoot 'axure_cli.py') @args
exit $LASTEXITCODE
