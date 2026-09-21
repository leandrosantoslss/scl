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

$required = @("SECRET_KEY", "SCL_TARGET_DATABASE_URL", "SCL_TEST_DATABASE_URL")
$placeholders = @("CHANGE_ME", "SCL_DB_USER", "SCL_DB_HOST", "SCL_DB_NAME", "SCL_TEST_USER", "SCL_TEST_HOST")
foreach ($name in $required) {
    $value = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not $value) {
        throw "Required local variable is missing or still contains a placeholder: $name"
    }
    foreach ($placeholder in $placeholders) {
        if ($value.Contains($placeholder)) {
            throw "Required local variable is missing or still contains a placeholder: $name"
        }
    }
}

$python = @'
import json
import os

import psycopg2
from psycopg2 import sql


connection = psycopg2.connect(
    os.environ["SCL_TARGET_DATABASE_URL"],
    connect_timeout=10,
    application_name="scl_gate_zero_readonly",
)
connection.set_session(readonly=True, autocommit=True)

tables = [
    "licencas_cliente",
    "licencas_sistema",
    "licencas_clientesistema",
    "licencas_acessomaquina",
]

with connection.cursor() as cursor:
    cursor.execute("SELECT current_database(), current_setting('server_version')")
    database, server_version = cursor.fetchone()

    cursor.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    public_tables = [row[0] for row in cursor.fetchall()]

    counts = {}
    for table in tables:
        cursor.execute("SELECT to_regclass(%s)", (f"public.{table}",))
        if cursor.fetchone()[0] is None:
            counts[table] = None
            continue
        cursor.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
        counts[table] = cursor.fetchone()[0]

test_connection = psycopg2.connect(
    os.environ["SCL_TEST_DATABASE_URL"],
    connect_timeout=10,
    application_name="scl_gate_zero_test_readonly",
)
test_connection.set_session(readonly=True, autocommit=True)
with test_connection.cursor() as cursor:
    cursor.execute("SELECT current_database(), current_setting('server_version')")
    test_database, test_server_version = cursor.fetchone()

if database == test_database:
    raise RuntimeError("Authoritative and test databases must be different.")

print(json.dumps({
    "database": database,
    "server_version": server_version,
    "public_tables": public_tables,
    "table_counts": counts,
    "test_database": test_database,
    "test_server_version": test_server_version,
}, sort_keys=True))
test_connection.close()
connection.close()
'@

$temporaryScript = Join-Path ([System.IO.Path]::GetTempPath()) ("scl-gate-zero-" + [guid]::NewGuid().ToString("N") + ".py")
try {
    Set-Content -LiteralPath $temporaryScript -Value $python -Encoding UTF8
    & python $temporaryScript
    if ($LASTEXITCODE -ne 0) {
        throw "Read-only PostgreSQL validation failed."
    }
}
finally {
    Remove-Item -LiteralPath $temporaryScript -Force -ErrorAction SilentlyContinue
}
