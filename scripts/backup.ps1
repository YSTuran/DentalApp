param(
    [string]$Destination = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envPath = Join-Path $projectRoot "backend\.env"
. (Join-Path $PSScriptRoot "backup-common.ps1")

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "backend/.env bulunamadı."
}
$encryptionMetadata = Get-EncryptionKeyMetadata $envPath

$backupRoot = if ($Destination) {
    [IO.Path]::GetFullPath($Destination)
} else {
    Join-Path $projectRoot "backups"
}
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$backupRoot = (Resolve-Path -LiteralPath $backupRoot).Path

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$finalPath = Join-Path $backupRoot "dentalapp-$stamp"
$stagingPath = Join-Path $backupRoot (".incomplete-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $stagingPath | Out-Null

$databaseUrl = (Get-EnvValue $envPath "DATABASE_URL").Replace(
    "postgresql+psycopg://",
    "postgresql://"
)
$databaseUri = [Uri]$databaseUrl
$credentials = $databaseUri.UserInfo -split ":", 2
$databaseUser = [Uri]::UnescapeDataString($credentials[0])
$databasePassword = if ($credentials.Count -gt 1) {
    [Uri]::UnescapeDataString($credentials[1])
} else { "" }
$databaseName = $databaseUri.AbsolutePath.TrimStart("/")
$databasePort = if ($databaseUri.Port -gt 0) { $databaseUri.Port } else { 5432 }

try {
    Push-Location (Join-Path $projectRoot "backend")
    try {
        & ".\.venv\Scripts\python.exe" -m app.cli.check_storage
        $storageExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($storageExitCode -eq 2) {
        throw "Yedekleme durduruldu: veritabanında kayıtlı bir veya daha fazla dosya eksik."
    }
    if ($storageExitCode -eq 1) {
        Write-Warning "Storage içinde sahipsiz dosyalar var; yedeğe yalnızca cases içeriği alınacak."
    }

    $dumpPath = Join-Path $stagingPath "database.dump"
    $previousPgPassword = $env:PGPASSWORD
    $env:PGPASSWORD = $databasePassword
    try {
        & pg_dump --host $databaseUri.Host --port $databasePort --username $databaseUser `
            --dbname $databaseName --format custom --file $dumpPath
        if ($LASTEXITCODE -ne 0) { throw "pg_dump başarısız oldu." }
    } finally {
        $env:PGPASSWORD = $previousPgPassword
    }

    $storageCases = Join-Path $projectRoot "storage\cases"
    if (Test-Path -LiteralPath $storageCases) {
        Copy-Item -LiteralPath $storageCases -Destination (Join-Path $stagingPath "cases") `
            -Recurse
    }
    $firebaseExport = Join-Path $projectRoot "firebase-export"
    if (Test-Path -LiteralPath $firebaseExport) {
        Copy-Item -LiteralPath $firebaseExport `
            -Destination (Join-Path $stagingPath "firebase-export") -Recurse
    }

    $files = Get-ChildItem -LiteralPath $stagingPath -File -Recurse | ForEach-Object {
        [ordered]@{
            path = $_.FullName.Substring($stagingPath.Length).TrimStart("\", "/").Replace("\", "/")
            bytes = $_.Length
            sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower()
        }
    }
    $manifest = [ordered]@{
        format = 2
        created_at = (Get-Date).ToUniversalTime().ToString("o")
        database = $databaseName
        encryption = $encryptionMetadata
        files = @($files)
    }
    $manifest | ConvertTo-Json -Depth 5 | Set-Content `
        -LiteralPath (Join-Path $stagingPath "manifest.json") -Encoding UTF8

    Move-Item -LiteralPath $stagingPath -Destination $finalPath
    Write-Output "Yedek oluşturuldu: $finalPath"
} catch {
    if (Test-Path -LiteralPath $stagingPath) {
        Remove-Item -LiteralPath $stagingPath -Recurse -Force
    }
    throw
}
