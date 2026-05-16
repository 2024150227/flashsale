#!/bin/bash

SSL_DIR="$(dirname "$0")/../nginx/ssl"
mkdir -p "$SSL_DIR"

echo "Generating self-signed SSL certificate..."

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/key.pem" \
    -out "$SSL_DIR/cert.pem" \
    -subj "/C=CN/ST=State/L=City/O=FlashSale/OU=Dev/CN=localhost" \
    2>/dev/null

echo "SSL certificate generated successfully!"
echo "  - $SSL_DIR/key.pem"
echo "  - $SSL_DIR/cert.pem"
echo ""
echo "Note: This is a self-signed certificate and will show as untrusted in browsers."
echo "For production, use a valid certificate from Let's Encrypt or another CA."
