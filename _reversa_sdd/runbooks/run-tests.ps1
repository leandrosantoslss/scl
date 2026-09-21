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

$testDatabaseUrl = [Environment]::GetEnvironmentVariable("SCL_TEST_DATABASE_URL", "Process")
if (-not $testDatabaseUrl) {
    throw "SCL_TEST_DATABASE_URL is required to run tests against the disposable database."
}

[Environment]::SetEnvironmentVariable("DATABASE_URL", $testDatabaseUrl, "Process")
[Environment]::SetEnvironmentVariable("SECRET_KEY", "test-only-key", "Process")
[Environment]::SetEnvironmentVariable("DEBUG", "true", "Process")
[Environment]::SetEnvironmentVariable("ALLOWED_HOSTS", "localhost,127.0.0.1", "Process")

Set-Location $projectRoot

$pytestArguments = @("-m", "pytest") + $args
& python @pytestArguments
exit $LASTEXITCODE
