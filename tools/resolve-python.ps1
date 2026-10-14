function Resolve-ReverseCliPython {
    param([string]$Repository, [string]$Preferred)
    $candidate = if ($Preferred) { $Preferred } else { $env:REVERSE_CLI_PYTHON }
    $configPath = if ($env:REVERSE_CLI_CONFIG) { $env:REVERSE_CLI_CONFIG } else { Join-Path $Repository 'reverse-cli.local.json' }
    if (-not $candidate -and (Test-Path -LiteralPath $configPath)) {
        $candidate = (Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json).python
    }
    if ($candidate) {
        if (-not (Test-Path -LiteralPath $candidate)) { throw 'Configured Python does not exist.' }
        return $candidate
    }
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw 'Python 3.11+ is required; set REVERSE_CLI_PYTHON or configure reverse-cli.local.json.'
}
