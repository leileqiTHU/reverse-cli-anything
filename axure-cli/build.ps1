$ErrorActionPreference='Stop'
$taskCache = if ($env:REVERSE_CLI_CACHE_DIR) { $env:REVERSE_CLI_CACHE_DIR } else { 'D:\Caches\reverse-cli' }
$env:TEMP=Join-Path $taskCache 'axure/temp'
$env:TMP=$env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP,(Join-Path $PSScriptRoot '.runtime') | Out-Null
$name='AxureBridge-'+[Guid]::NewGuid().ToString('N')+'.dll'
$output=Join-Path $PSScriptRoot ".runtime\$name"
Add-Type -Path @('Backend.cs','PageCommands.cs','WidgetCommands.cs','InteractionCommands.cs','InteractionExpressions.cs','StartupHook.cs' | ForEach-Object {Join-Path $PSScriptRoot $_}) -OutputAssembly $output
@{path=$output;builtUtc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot '.runtime\bridge-build.json') -Encoding utf8
@{ok=$true;assembly=$output} | ConvertTo-Json -Compress
