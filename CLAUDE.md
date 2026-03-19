# Reference Documents

- [FBTC 2025 Grantor Trust Tax Reporting Statement](docs/fbtc-2025-grantor-trust-tax-reporting.md) — Fidelity's WHFIT tax reporting guidance including the 6-step gain/loss and basis calculation example for FBTC shareholders.

# Testing

- Prefer mocks over filesystem/expensive resources in unit tests
- Reserve real filesystem, databases, and network for integration tests only
- Every task must achieve 90%+ test coverage on files it creates or modifies
- Verify with: `pytest --cov=fbtc_taxgrinder --cov-report=term-missing --cov-fail-under=90`
