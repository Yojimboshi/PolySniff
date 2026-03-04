# Scripts Directory

Simple test scripts for API and modeling.

## API Test

```bash
python scripts/test_api.py
```

Fetches latest 5 open markets from Polymarket API and prints summaries. Saves raw JSON to `scripts/markets_sample.json` for inspection.

**Purpose**: Understand Polymarket API response structure and available fields.

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

## Modeling Test

```bash
python scripts/test_model.py
```

Tests the full pipeline:
1. Feature extraction from mock market data
2. Probability engine prediction
3. EV calculation

**Purpose**: Verify the modeling pipeline works end-to-end with mock data.
