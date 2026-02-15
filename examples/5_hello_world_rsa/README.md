# Hello World with RSA Encryption Example

This example demonstrates how to use RSA encryption with INTERSECT services.

## Overview

RSA encryption provides end-to-end encryption for messages between clients and services:
- Clients encrypt requests using the service's public key
- Services encrypt responses using the client's public key
- Each party decrypts messages using their own private key

## Files

- `hello_service.py` - Service implementation with RSA encryption enabled
- `hello_client.py` - Client implementation that sends RSA encrypted messages
- `hello_service_schema.json` - Service schema defining available operations

## Key Features

1. **Automatic RSA Key Generation**:
   - Both service and client automatically generate RSA key pairs internally
   - No manual key management required
   - Service automatically handles public key requests from clients

2. **Transparent Encryption**:
   - Simply set `encryption_scheme='RSA'` when sending messages
   - INTERSECT SDK handles all encryption/decryption automatically
   - Public key exchange happens automatically in the background

## Running the Example

1. Start the service:
   ```bash
   python -m examples.5_hello_world_rsa.hello_service
   ```

2. In another terminal, run the client:
   ```bash
   python -m examples.5_hello_world_rsa.hello_client
   ```

## Expected Output

Client output:
```
Hello, hello_client!
```

## How It Works

1. Client starts and generates its RSA key pair
2. Client sends encrypted message to service (encryption_scheme='RSA')
3. Client first fetches service's public key via `intersect_sdk.get_public_key`
4. Client encrypts the request using service's public key
5. Service receives encrypted request and decrypts it using its private key
6. Service processes the request and generates a response
7. Service fetches client's public key (if not cached)
8. Service encrypts response using client's public key
9. Client receives encrypted response and decrypts it using its private key
10. Client prints the decrypted response

## Security Notes

- Each service and client automatically generates its own unique RSA key pair on startup
- Private keys are managed internally by the SDK and never transmitted
- Public keys are exchanged automatically via the INTERSECT messaging system
- RSA encryption uses 2048-bit keys for strong security
- No manual key management is required - the SDK handles everything automatically
