param([int]$Port = 8787)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Write-Host 'Genesis — local company OS'
Write-Host 'API credentials stay in this process environment; nothing is saved to disk.'
$genesisConfigured = $env:GENESIS_OPENAI_API_KEY -or $env:OPENAI_API_KEY -or $env:GENESIS_ANTHROPIC_API_KEY -or $env:ANTHROPIC_API_KEY -or $env:GENESIS_GEMINI_API_KEY -or $env:GEMINI_API_KEY -or $env:GOOGLE_API_KEY
if (-not $genesisConfigured) {
    $genesisChoice = Read-Host 'Provider: 1 OpenAI, 2 Anthropic, 3 Gemini, Enter to launch without AI'
    $genesisKeyName = switch ($genesisChoice) {
        '1' { 'GENESIS_OPENAI_API_KEY' }
        '2' { 'GENESIS_ANTHROPIC_API_KEY' }
        '3' { 'GENESIS_GEMINI_API_KEY' }
        default { $null }
    }
    if ($genesisKeyName) {
        $genesisSecureKey = Read-Host 'API key (hidden)' -AsSecureString
        $genesisKeyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($genesisSecureKey)
        try {
            [Environment]::SetEnvironmentVariable($genesisKeyName, [Runtime.InteropServices.Marshal]::PtrToStringBSTR($genesisKeyPointer), 'Process')
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($genesisKeyPointer)
            $genesisSecureKey.Dispose()
        }
    }
}
try {
    Write-Host "Open http://127.0.0.1:$Port in your browser. Ctrl+C stops Genesis."
    python -m genesis --port $Port
} finally {
    if ($genesisKeyName) { [Environment]::SetEnvironmentVariable($genesisKeyName, $null, 'Process') }
}
