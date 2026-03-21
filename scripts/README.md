# Scripts Directory

Simple test scripts for API and modeling.

**Market JSON** (categorized exports, samples, filtered outputs) lives in **`data/`** at the repo root, not in this folder. That directory is listed in `.gitignore` so large files stay local unless you force-add them.

## API Test

```bash
python scripts/test_api.py
```

Fetches latest 5 open markets from Polymarket API and prints summaries. Large categorized output is written to `data/categorized_markets.json` (repo root; see `.gitignore`).

**Purpose**: Understand Polymarket API response structure and available fields.

## Filter top markets

```bash
python scripts/filter_markets.py
```

Defaults: read `data/categorized_markets.json`, write `data/filtered_marketData.json` (top 50 per category; optional `input.json output.json` and `-n N`).

## Get API Keys

```bash
python scripts/get_api_keys.py
```

Generates Polymarket API credentials (apiKey, secret, passphrase) via wallet signature.

**Flow**:
1. Requests challenge message from Polymarket API
2. Signs challenge with your wallet private key
3. Exchanges signature for API credentials

**Requirements**:
- `eth-account` package: `pip install eth-account`
- Wallet private key (hex format)

**Security**: The script runs locally and only uses your private key to sign the challenge. Never share your private key or API credentials.

**Purpose**: Generate API keys needed for authenticated trading endpoints on Polymarket.
