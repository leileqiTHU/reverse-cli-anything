# Compatibility entry point for existing local commands.
& (Join-Path $PSScriptRoot 'capcut-cli\capcut-agent.ps1') @args
exit $LASTEXITCODE
