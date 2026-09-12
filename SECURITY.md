# Security

This public repository contains no production credentials or endpoints. The deployed pattern uses an encrypted SSM SecureString read by a narrowly scoped Lambda execution role and compares the supplied header with `hmac.compare_digest` before parsing business input.

The service is intentionally a low-risk classifier. It does **not** send customer messages, mutate CRM ownership, schedule appointments, or perform irreversible business actions. The caller retains an existing fallback path if this service times out or returns a non-2xx response.

Do not file real secrets or customer payloads in issues. Rotate any credential immediately if it is ever exposed.
