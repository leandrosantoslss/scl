param(
    [switch]$Authoritative
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$envPath = Join-Path $projectRoot ".env"

Get-Content -LiteralPath $envPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        return
    }

    $parts = $line.Split("=", 2)
    if ($parts.Count -ne 2) {
        throw "Invalid .env entry."
    }

    $name = $parts[0].Trim()
    $value = $parts[1].Trim().Trim('"').Trim("'")
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
}

if ($Authoritative) {
    $databaseUrl = [Environment]::GetEnvironmentVariable("SCL_TARGET_DATABASE_URL", "Process")
    if (-not $databaseUrl) {
        throw "SCL_TARGET_DATABASE_URL is required for authoritative database operations."
    }
} else {
    $databaseUrl = [Environment]::GetEnvironmentVariable("SCL_TEST_DATABASE_URL", "Process")
    if (-not $databaseUrl) {
        throw "SCL_TEST_DATABASE_URL is required for disposable test database operations."
    }
}

[Environment]::SetEnvironmentVariable("DATABASE_URL", $databaseUrl, "Process")

if (-not [Environment]::GetEnvironmentVariable("SECRET_KEY", "Process")) {
    [Environment]::SetEnvironmentVariable("SECRET_KEY", "test-only-key", "Process")
}

Set-Location $projectRoot

$manageArguments = @("manage.py") + $args
& python @manageArguments
exit $LASTEXITCODE
