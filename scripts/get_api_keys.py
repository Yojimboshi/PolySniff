"""Generate Polymarket API credentials using the official SDK."""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from py_clob_client.client import ClobClient

# Configure logging - set to INFO to avoid httpcore/hpack debug spam
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress noisy httpcore/hpack debug logs
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Load .env
load_dotenv()


def main():
    """Generate API credentials using the SDK."""
    logger.debug("Starting API credential generation")
    
    # Get private key
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        logger.error("PRIVATE_KEY not found in .env")
        print("Error: PRIVATE_KEY not found in .env")
        return
    
    logger.debug(f"Private key loaded (length: {len(private_key)})")
    
    try:
        # Initialize the CLOB client
        logger.debug("Initializing ClobClient...")
        client = ClobClient(
            host="https://clob.polymarket.com",
            chain_id=137,  # Polygon mainnet
            key=private_key
        )
        
        logger.debug("Creating or deriving API credentials...")
        # Creates new credentials or derives existing ones
        credentials = client.create_or_derive_api_creds()
        
        logger.info("API credentials retrieved successfully")
        print("\nAPI Credentials:")
        print(f"  API Key: {credentials.api_key}")
        print(f"  Secret: {credentials.api_secret}")
        print(f"  Passphrase: {credentials.api_passphrase}")
        
        # Save to file
        output_file = Path("scripts/api_keys.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert ApiCreds object to dict for JSON serialization
        credentials_dict = {
            "apiKey": credentials.api_key,
            "secret": credentials.api_secret,
            "passphrase": credentials.api_passphrase
        }
        
        with open(output_file, "w") as f:
            json.dump(credentials_dict, f, indent=2)
        
        logger.info(f"Saved credentials to {output_file}")
        print(f"\nSaved to {output_file}")
        
    except Exception as e:
        logger.exception("Exception occurred while getting API credentials")
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
