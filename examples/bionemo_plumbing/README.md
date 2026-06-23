# BioNeMo plumbing example

Proves the full evidence loop offline: a cached BioNeMo NIM response + a fenced synthetic
corroborator drive one claim to `LICENSED`, then `certify` emits a certificate.

## Run (offline, from a cassette)

```bash
uv run --project . python -m examples.bionemo_plumbing.run
# prints: Status.LICENSED
```

## Certify

```bash
# run.certify_plumbing() builds the certificate in-process; or via the CLI on a saved corpus:
polymer-claims certify bionemo-plumbing-1 --corpus <saved-corpus.json> --format text
```

## Going live (real NIM)

1. Store the key in the macOS keychain (never a dotfile):
   ```bash
   security add-generic-password -s nvidia-build-api -a "$USER" -w <YOUR_NVIDIA_API_KEY>
   ```
2. Run the live smoke test against a hosted NIM:
   ```bash
   POLYMER_BIONEMO_LIVE=1 POLYMER_BIONEMO_ENDPOINT=<nim-url> \
     uv run --project . pytest tests/bionemo/test_live_smoke.py -v
   ```
   build.nvidia.com starts with free credits; responses cache to disk so re-runs do not reburn them.

## The synthetic-corroborator fence

`tests/fixtures/synthetic_corroborator.py` is a TEST DOUBLE. Its credential (owner
`polymer-claims-test`) may appear ONLY in a plumbing `AdapterRegistry` — never in
`polymer_claims.bionemo.registry`. The air-gap needs two independently-owned adapters; when a
real wedge is chosen (variant-effect scoring + an independent VEP, etc.), the double is replaced
by a real second model and barred from any certifying run.
