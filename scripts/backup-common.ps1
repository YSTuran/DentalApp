function Get-EnvValue([string]$Path, [string]$Name) {
    $line = Get-Content -LiteralPath $Path | Where-Object {
        $_ -match "^\s*$([regex]::Escape($Name))\s*="
    } | Select-Object -Last 1
    if (-not $line) { throw "$Name backend/.env içinde bulunamadı." }
    return ($line -split "=", 2)[1].Trim().Trim('"').Trim("'")
}

function Get-KeyFingerprint([string]$EncodedKey, [string]$SettingName) {
    try {
        $keyBytes = [Convert]::FromBase64String($EncodedKey)
    } catch {
        throw "$SettingName geçerli Base64 biçiminde değil."
    }
    if ($keyBytes.Length -ne 32) {
        throw "$SettingName tam olarak 32 bayt olmalıdır."
    }

    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString($sha256.ComputeHash($keyBytes)).Replace("-", "").ToLower()
    } finally {
        $sha256.Dispose()
    }
}

function Get-EncryptionKeyMetadata([string]$EnvPath) {
    try {
        $configuredKeys = Get-EnvValue $EnvPath "PATIENT_DATA_KEYS" | ConvertFrom-Json
    } catch {
        throw "PATIENT_DATA_KEYS geçerli bir JSON nesnesi olmalıdır."
    }

    $keyProperties = @($configuredKeys.PSObject.Properties)
    if ($keyProperties.Count -eq 0) {
        throw "PATIENT_DATA_KEYS en az bir anahtar içermelidir."
    }

    $fingerprints = [ordered]@{}
    foreach ($property in $keyProperties) {
        $fingerprints[$property.Name] = Get-KeyFingerprint `
            ([string]$property.Value) "PATIENT_DATA_KEYS[$($property.Name)]"
    }

    $activeKeyId = Get-EnvValue $EnvPath "PATIENT_DATA_ACTIVE_KEY_ID"
    if (-not $fingerprints.Contains($activeKeyId)) {
        throw "PATIENT_DATA_ACTIVE_KEY_ID, PATIENT_DATA_KEYS içinde bulunamadı."
    }

    return [pscustomobject][ordered]@{
        active_key_id = $activeKeyId
        data_key_fingerprints = $fingerprints
        lookup_key_fingerprint = Get-KeyFingerprint `
            (Get-EnvValue $EnvPath "PATIENT_LOOKUP_KEY") "PATIENT_LOOKUP_KEY"
    }
}

function Assert-EncryptionKeyCompatibility([object]$Manifest, [string]$EnvPath) {
    if ($null -eq $Manifest.encryption) {
        Write-Warning "Bu eski yedekte şifreleme anahtarı parmak izi yok; uyumluluk doğrulanamadı."
        return
    }
    if ($null -eq $Manifest.encryption.data_key_fingerprints -or
        -not $Manifest.encryption.lookup_key_fingerprint) {
        throw "Yedek manifestindeki şifreleme anahtarı bilgisi eksik."
    }

    $current = Get-EncryptionKeyMetadata $EnvPath
    $backupFingerprints = $Manifest.encryption.data_key_fingerprints
    $entries = if ($backupFingerprints -is [Collections.IDictionary]) {
        @($backupFingerprints.GetEnumerator() | ForEach-Object {
            [pscustomobject]@{ Name = $_.Key; Value = $_.Value }
        })
    } else {
        @($backupFingerprints.PSObject.Properties | Where-Object {
            $_.MemberType -eq "NoteProperty"
        })
    }
    if ($entries.Count -eq 0) {
        throw "Yedek manifestinde veri şifreleme anahtarı parmak izi yok."
    }

    foreach ($entry in $entries) {
        if (-not $current.data_key_fingerprints.Contains([string]$entry.Name)) {
            throw "Mevcut PATIENT_DATA_KEYS içinde yedeğin '$($entry.Name)' anahtarı yok."
        }
        if ($current.data_key_fingerprints[[string]$entry.Name] -cne [string]$entry.Value) {
            throw "PATIENT_DATA_KEYS[$($entry.Name)] bu yedekle uyumlu değil."
        }
    }
    if ($current.lookup_key_fingerprint -cne
        [string]$Manifest.encryption.lookup_key_fingerprint) {
        throw "PATIENT_LOOKUP_KEY bu yedekle uyumlu değil."
    }
}
