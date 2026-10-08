param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [switch]$Apply,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resolvedBackup = (Resolve-Path -LiteralPath $BackupPath).Path
$manifestPath = Join-Path $resolvedBackup "manifest.json"
$dumpPath = Join-Path $resolvedBackup "database.dump"
$envPath = Join-Path $projectRoot "backend\.env"
. (Join-Path $PSScriptRoot "backup-common.ps1")

if (-not (Test-Path -LiteralPath $manifestPath) -or -not (Test-Path -LiteralPath $dumpPath)) {
    throw "Geçerli manifest.json ve database.dump bulunamadı."
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
foreach ($entry in $manifest.files) {
    $candidate = [IO.Path]::GetFullPath((Join-Path $resolvedBackup $entry.path))
    if (-not $candidate.StartsWith($resolvedBackup + [IO.Path]::DirectorySeparatorChar)) {
        throw "Manifest güvenli olmayan bir yol içeriyor: $($entry.path)"
    }
    if (-not (Test-Path -LiteralPath $candidate)) { throw "Yedek dosyası eksik: $($entry.path)" }
    $actualHash = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash.ToLower()
    if ($actualHash -ne $entry.sha256) { throw "Yedek bütünlüğü bozuk: $($entry.path)" }
}
Assert-EncryptionKeyCompatibility $manifest $envPath

Write-Output "Yedek doğrulandı: $resolvedBackup"
if (-not $Apply) {
    Write-Output "Geri yükleme yapılmadı. Uygulamak için -Apply kullanın."
    exit 0
}
if (-not $Force) {
    $confirmation = Read-Host "Mevcut veritabanı ve vaka dosyaları değiştirilecek. RESTORE yazın"
    if ($confirmation -cne "RESTORE") { throw "Geri yükleme iptal edildi." }
}

& (Join-Path $PSScriptRoot "backup.ps1") | Write-Output

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

$rollbackRoot = Join-Path $projectRoot ("storage\restore-rollback-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $rollbackRoot | Out-Null
$currentCases = Join-Path $projectRoot "storage\cases"
$backupCases = Join-Path $resolvedBackup "cases"
$currentFirebase = Join-Path $projectRoot "firebase-export"
$backupFirebase = Join-Path $resolvedBackup "firebase-export"

try {
    if (Test-Path -LiteralPath $currentCases) {
        Move-Item -LiteralPath $currentCases -Destination (Join-Path $rollbackRoot "cases")
    }
    if (Test-Path -LiteralPath $backupCases) {
        Copy-Item -LiteralPath $backupCases -Destination $currentCases -Recurse
    }
    if (Test-Path -LiteralPath $currentFirebase) {
        Move-Item -LiteralPath $currentFirebase `
            -Destination (Join-Path $rollbackRoot "firebase-export")
    }
    if (Test-Path -LiteralPath $backupFirebase) {
        Copy-Item -LiteralPath $backupFirebase -Destination $currentFirebase -Recurse
    }

    $previousPgPassword = $env:PGPASSWORD
    $env:PGPASSWORD = $databasePassword
    try {
        & pg_restore --host $databaseUri.Host --port $databasePort --username $databaseUser `
            --dbname $databaseName --clean --if-exists --no-owner --single-transaction $dumpPath
        if ($LASTEXITCODE -ne 0) { throw "pg_restore başarısız oldu." }
    } finally {
        $env:PGPASSWORD = $previousPgPassword
    }
    Write-Output "Geri yükleme tamamlandı. Dosya geri dönüş noktası: $rollbackRoot"
} catch {
    if (Test-Path -LiteralPath $currentCases) {
        Remove-Item -LiteralPath $currentCases -Recurse -Force
    }
    $rollbackCases = Join-Path $rollbackRoot "cases"
    if (Test-Path -LiteralPath $rollbackCases) {
        Move-Item -LiteralPath $rollbackCases -Destination $currentCases
    }
    if (Test-Path -LiteralPath $currentFirebase) {
        Remove-Item -LiteralPath $currentFirebase -Recurse -Force
    }
    $rollbackFirebase = Join-Path $rollbackRoot "firebase-export"
    if (Test-Path -LiteralPath $rollbackFirebase) {
        Move-Item -LiteralPath $rollbackFirebase -Destination $currentFirebase
    }
    throw
}
