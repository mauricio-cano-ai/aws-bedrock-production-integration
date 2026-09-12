# Contributing

1. Create a branch from `main`.
2. Install with `python -m pip install -e ".[dev]"`.
3. Run `make verify`.
4. For infrastructure changes also run `sam validate --lint && sam build`.
5. Keep deterministic tests independent of AWS credentials.
6. Never commit real API keys, account IDs, tenant data, production URLs, or captured lead text.

Pull requests should explain the invariant being protected, the failure mode addressed, and the test that would fail without the change.
