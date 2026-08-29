param(
    [string]$OutputDirectory = "artifacts/git-upload"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$outputRoot = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot $OutputDirectory))

if (-not $outputRoot.StartsWith($repositoryRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputDirectory must stay inside the repository."
}

$backendRoot = Join-Path $outputRoot "chhabi-backend-website"
$mobileRoot = Join-Path $outputRoot "chhabi-mobile"

if (Test-Path -LiteralPath $outputRoot) {
    Remove-Item -LiteralPath $outputRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $backendRoot, $mobileRoot -Force | Out-Null

Push-Location $repositoryRoot
try {
    $backendArchivePath = Join-Path $outputRoot "backend-source.tar"
    $mobileArchivePath = Join-Path $outputRoot "mobile-source.tar"
    git archive --format=tar --output=$backendArchivePath HEAD
    if ($LASTEXITCODE -ne 0) {
        throw "Backend git archive failed."
    }

    tar -xf $backendArchivePath -C $backendRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Backend tar extraction failed."
    }

    $mobilePlaceholder = Join-Path $backendRoot "mobile"
    if (Test-Path -LiteralPath $mobilePlaceholder) {
        Remove-Item -LiteralPath $mobilePlaceholder -Recurse -Force
    }

    git -C mobile archive --format=tar --output=$mobileArchivePath HEAD
    if ($LASTEXITCODE -ne 0) {
        throw "Mobile git archive failed."
    }
    tar -xf $mobileArchivePath -C $mobileRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Mobile tar extraction failed."
    }

    Remove-Item -LiteralPath $backendArchivePath, $mobileArchivePath -Force
}
finally {
    Pop-Location
}

@"
Generated from Git-tracked files only.

Before deployment:
1. Copy .env.dist to .env and fill production secrets locally.
2. Run migrations and collectstatic on the server.
3. Restore user-uploaded media from private storage/backup, never from public Git.
"@ | Set-Content -LiteralPath (Join-Path $backendRoot "UPLOAD-NOTES.txt") -Encoding UTF8

@"
Generated from the mobile/ Git-tracked files only.

Before building:
1. Run npm install.
2. Set src/config.ts API_BASE_URL to the deployed HTTPS backend.
3. Keep Android/iOS signing keys outside Git.
"@ | Set-Content -LiteralPath (Join-Path $mobileRoot "UPLOAD-NOTES.txt") -Encoding UTF8

Write-Output "Backend + website: $backendRoot"
Write-Output "Mobile app:         $mobileRoot"
