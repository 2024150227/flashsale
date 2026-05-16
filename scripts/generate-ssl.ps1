$ErrorActionPreference = "Stop"

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$SslDir = Join-Path $ScriptPath "..\nginx\ssl"

if (-not (Test-Path $SslDir)) {
    New-Item -ItemType Directory -Path $SslDir -Force | Out-Null
}

Write-Host "Generating self-signed SSL certificate..." -ForegroundColor Green

$CertPath = Join-Path $SslDir "cert.pem"
$KeyPath = Join-Path $SslDir "key.pem"

try {
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
        -keyout $KeyPath `
        -out $CertPath `
        -subj "/C=CN/ST=State/L=City/O=FlashSale/OU=Dev/CN=localhost"
    
    Write-Host ""
    Write-Host "SSL certificate generated successfully!" -ForegroundColor Green
    Write-Host "  - $KeyPath"
    Write-Host "  - $CertPath"
    Write-Host ""
    Write-Host "Note: This is a self-signed certificate and will show as untrusted in browsers." -ForegroundColor Yellow
    Write-Host "For production, use a valid certificate from Let's Encrypt or another CA." -ForegroundColor Yellow
}
catch {
    Write-Host "Error generating SSL certificate: $_" -ForegroundColor Red
    Write-Host "Make sure you have OpenSSL installed and in your PATH." -ForegroundColor Yellow
    exit 1
}
