# Release checklist

This checklist prepares a release without changing Zellomon production code or credentials.

## Required before public publication

- [x] Package builds as a wheel.
- [x] Unit tests cover connection payloads and secret redaction.
- [x] Live examples require an explicit opt-in flag.
- [x] Example output redacts passwords, auth tokens, refresh tokens, signing keys, and private keys.
- [x] Friends & Family and Zello Work authentication modes are documented separately.
- [x] Python 3.10, 3.11, and 3.12 are configured in CI.
- [x] PyPI publication uses Trusted Publishing/OIDC; no PyPI API token belongs in the repository.
- [x] Use Pyzel as the public project/distribution name. Zello is referenced only descriptively for API compatibility; this reduces branding risk but is not legal clearance.
- [x] MIT licence retained from the existing Pyzel repository.
- [ ] Configure the PyPI Trusted Publisher for the final distribution name and the GitHub `pypi` environment.
- [ ] Run an owner-authorized live smoke test against a non-production/test channel and confirm the logon response succeeds without printing credentials.
- [ ] Publish a GitHub release only after the preceding checks are complete.

## Live smoke test

Use an account and channel specifically approved for testing. Do not use Zellomon's production Bruce account as a package release test.

```bash
PYZEL_LIVE_TEST=1 \
ZELLO_CHANNEL=ExampleChannel \
ZELLO_USERNAME=example-user \
ZELLO_PASSWORD='...' \
ZELLO_AUTH_TOKEN='...' \
python examples/live_connect.py
```

For Zello Work, set the network endpoint and omit the Friends & Family auth token.

## Rollback

The package is developed in its own repository. No Pyzel release step should modify Zellomon, its Render startup command, its account parsing, or its production authentication configuration.
