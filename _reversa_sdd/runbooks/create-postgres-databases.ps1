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

$python = @'
import json
import os
from urllib.parse import urlsplit, urlunsplit

import psycopg2
from psycopg2 import sql


def create_database(url):
    parsed = urlsplit(url)
    database = parsed.path.lstrip("/")
    if not database:
        raise RuntimeError("Database name is missing from URL.")

    maintenance_url = urlunsplit((
        parsed.scheme,
        parsed.netloc,
        "/postgres",
        parsed.query,
        parsed.fragment,
    ))
    connection = psycopg2.connect(
        maintenance_url,
        connect_timeout=10,
        application_name="scl_gate_zero_database_setup",
    )
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
        if cursor.fetchone() is not None:
            result = "existing"
        else:
            cursor.execute(
                sql.SQL("CREATE DATABASE {} WITH TEMPLATE template0 ENCODING 'UTF8'").format(
                    sql.Identifier(database)
                )
            )
            result = "created"
    connection.close()
    return database, result


target_name, target_result = create_database(os.environ["SCL_TARGET_DATABASE_URL"])
test_name, test_result = create_database(os.environ["SCL_TEST_DATABASE_URL"])
if target_name == test_name:
    raise RuntimeError("Authoritative and test database names must be different.")

print(json.dumps({
    "authoritative_database": target_name,
    "authoritative_result": target_result,
    "test_database": test_name,
    "test_result": test_result,
}, sort_keys=True))
'@

$temporaryScript = Join-Path ([System.IO.Path]::GetTempPath()) ("scl-create-databases-" + [guid]::NewGuid().ToString("N") + ".py")
try {
    Set-Content -LiteralPath $temporaryScript -Value $python -Encoding UTF8
    & python $temporaryScript
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL database creation failed."
    }
}
finally {
    Remove-Item -LiteralPath $temporaryScript -Force -ErrorAction SilentlyContinue
}
