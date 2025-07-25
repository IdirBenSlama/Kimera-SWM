#!/usr/bin/env python3
"""
CDP V2 REAL TRADER - LIVE MONEY
===============================

Real trader for Coinbase Developer Platform API v2.
This will place ACTUAL ORDERS on your Coinbase account.

WARNING: THIS USES REAL MONEY
"""

import os
import sys
import json
import time
import asyncio
import requests
import hashlib
import hmac
import base64
from datetime import datetime
from typing import Dict, List, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

class CDPv2RealTrader:
    """
    Real trader for Coinbase Developer Platform API v2
    """
    
    def __init__(self, organization_id: str, api_key_id: str, private_key_pem: str):
        """
        Initialize CDP v2 real trader
        
        Args:
            organization_id: CDP organization ID
            api_key_id: CDP API key ID  
            private_key_pem: CDP private key in PEM format
        """
        self.organization_id = organization_id
        self.api_key_id = api_key_id
        self.private_key_pem = private_key_pem
        
        # CDP v2 API endpoints
        self.base_url = "https://api.developer.coinbase.com"
        
        print("🔥 CDP V2 REAL TRADER INITIALIZED")
        print(f"   Organization: {organization_id[:8]}...")
        print(f"   API Key: {api_key_id[:8]}...")
        print("   WARNING: THIS WILL PLACE REAL ORDERS")
        
        # Load the private key
        try:
            self.private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend()
            )
            print("✅ Private key loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load private key: {e}")
            self.private_key = None
    
    def create_jwt_token(self, request_path: str, method: str = 'GET', body: str = '') -> str:
        """Create JWT token for CDP v2 authentication"""
        try:
            import jwt
            
            # Create the payload
            uri = f"{method} {self.base_url}{request_path}"
            
            payload = {
                'sub': self.api_key_id,
                'iss': "cdp",
                'nbf': int(time.time()),
                'exp': int(time.time()) + 120,  # 2 minutes
                'uri': uri
            }
            
            # Sign with private key
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm='ES256',
                headers={'kid': self.api_key_id}
            )
            
            return token
            
        except Exception as e:
            print(f"❌ Failed to create JWT token: {e}")
            return None
    
    def get_headers(self, request_path: str, method: str = 'GET', body: str = '') -> Dict[str, str]:
        """Get authentication headers for CDP v2 API"""
        token = self.create_jwt_token(request_path, method, body)
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    async def test_authentication(self) -> bool:
        """Test CDP v2 authentication"""
        try:
            print("\n🔐 Testing CDP v2 authentication...")
            
            # Test endpoint - get organization info
            request_path = f"/platform/organizations/{self.organization_id}"
            headers = self.get_headers(request_path)
            
            response = requests.get(
                f"{self.base_url}{request_path}",
                headers=headers
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                org_data = response.json()
                print("✅ CDP v2 authentication successful!")
                print(f"   Organization: {org_data.get('name', 'Unknown')}")
                return True
            else:
                print(f"❌ Authentication failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication test failed: {e}")
            return False
    
    async def get_wallets(self) -> List[Dict]:
        """Get all wallets for the organization"""
        try:
            print("\n💰 Getting CDP wallets...")
            
            request_path = f"/platform/organizations/{self.organization_id}/wallets"
            headers = self.get_headers(request_path)
            
            response = requests.get(
                f"{self.base_url}{request_path}",
                headers=headers
            )
            
            if response.status_code == 200:
                wallets_data = response.json()
                wallets = wallets_data.get('data', [])
                
                print(f"✅ Found {len(wallets)} wallets:")
                for wallet in wallets:
                    print(f"   Wallet ID: {wallet.get('id')}")
                    print(f"   Name: {wallet.get('display_name', 'Unnamed')}")
                
                return wallets
            else:
                print(f"❌ Failed to get wallets: {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Failed to get wallets: {e}")
            return []
    
    async def get_wallet_balances(self, wallet_id: str) -> Dict[str, float]:
        """Get balances for a specific wallet"""
        try:
            print(f"\n💰 Getting balances for wallet {wallet_id[:8]}...")
            
            request_path = f"/platform/organizations/{self.organization_id}/wallets/{wallet_id}/balances"
            headers = self.get_headers(request_path)
            
            response = requests.get(
                f"{self.base_url}{request_path}",
                headers=headers
            )
            
            if response.status_code == 200:
                balances_data = response.json()
                balances = {}
                
                print("💰 Wallet balances:")
                for balance in balances_data.get('data', []):
                    asset = balance.get('asset', {}).get('asset_id', 'Unknown')
                    amount = float(balance.get('amount', 0))
                    balances[asset] = amount
                    print(f"   {asset}: {amount}")
                
                return balances
            else:
                print(f"❌ Failed to get balances: {response.text}")
                return {}
                
        except Exception as e:
            print(f"❌ Failed to get balances: {e}")
            return {}
    
    async def create_trade_order(self, wallet_id: str, asset_id: str, amount: str, side: str) -> Optional[Dict]:
        """
        Create a trade order on CDP v2
        
        Args:
            wallet_id: Wallet to trade from
            asset_id: Asset to trade (e.g., 'btc', 'eth')
            amount: Amount to trade
            side: 'buy' or 'sell'
        """
        try:
            print(f"\n🚀 CREATING REAL TRADE ORDER:")
            print(f"   Wallet: {wallet_id[:8]}...")
            print(f"   Asset: {asset_id}")
            print(f"   Amount: {amount}")
            print(f"   Side: {side}")
            print("   THIS IS REAL MONEY!")
            
            request_path = f"/platform/organizations/{self.organization_id}/wallets/{wallet_id}/orders"
            
            order_data = {
                'type': 'market_order',
                'side': side,
                'asset_id': asset_id,
                'amount': amount
            }
            
            body = json.dumps(order_data)
            headers = self.get_headers(request_path, 'POST', body)
            
            response = requests.post(
                f"{self.base_url}{request_path}",
                headers=headers,
                data=body
            )
            
            if response.status_code in [200, 201]:
                order_result = response.json()
                order = order_result.get('data', {})
                
                print(f"✅ REAL ORDER CREATED!")
                print(f"   Order ID: {order.get('id')}")
                print(f"   Status: {order.get('status')}")
                print(f"   Type: {order.get('type')}")
                
                return order
            else:
                print(f"❌ Order creation failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Failed to create order: {e}")
            return None
    
    async def test_small_trade(self) -> bool:
        """Test with a very small trade to verify everything works"""
        try:
            print("\n🧪 TESTING SMALL REAL TRADE")
            print("=" * 30)
            
            # Get wallets
            wallets = await self.get_wallets()
            if not wallets:
                print("❌ No wallets found")
                return False
            
            # Use first wallet
            wallet_id = wallets[0]['id']
            
            # Get balances
            balances = await self.get_wallet_balances(wallet_id)
            
            # Check for sufficient balance (need some base currency)
            if not balances:
                print("❌ No balances found")
                return False
            
            print(f"\n💡 Available for testing:")
            for asset, amount in balances.items():
                if amount > 0:
                    print(f"   {asset}: {amount}")
            
            # For testing, try a very small BTC buy if USD/EUR available
            test_amount = "0.01"  # Very small amount
            
            # Ask user confirmation
            response = input(f"\n🤔 Create test order for {test_amount} BTC? (yes/no): ")
            
            if response.lower() in ['yes', 'y']:
                order = await self.create_trade_order(
                    wallet_id=wallet_id,
                    asset_id='btc',
                    amount=test_amount,
                    side='buy'
                )
                
                if order:
                    print("✅ Test trade successful!")
                    print("   Check your Coinbase app - you should see this order")
                    return True
                else:
                    print("❌ Test trade failed")
                    return False
            else:
                print("🔍 Skipping test trade")
                return True
                
        except Exception as e:
            print(f"❌ Test trade failed: {e}")
            return False

async def main():
    """Test CDP v2 real trading"""
    print("🔥 CDP V2 REAL TRADER TEST")
    print("=" * 30)
    print("⚠️  WARNING: THIS USES REAL MONEY")
    print("⚠️  ORDERS WILL APPEAR IN YOUR COINBASE ACCOUNT")
    print("=" * 30)
    
    # Your CDP credentials
    ORGANIZATION_ID = "d5c46584-dd70-4be9-a71a-1e5e1b7a7ea3"
    API_KEY_ID = "dfe10f85-ed6c-4e75-a880-5db488c44f73"
    PRIVATE_KEY_PEM = """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIMyN35R0MUQewQ27M8ljhrGsQgRtIl1I3VMCZMucX4UIoAoGCCqGSM49
AwEHoUQDQgAERK6BZscG6p5nLQzIhPkUjXqIT9m/mw/S81U9di/u2BKRvujr4fUL
k+1M3dZ5l6SjNp2naYaa7oXuQQUm8UsFFA==
-----END EC PRIVATE KEY-----"""
    
    # Create trader
    trader = CDPv2RealTrader(ORGANIZATION_ID, API_KEY_ID, PRIVATE_KEY_PEM)
    
    if trader.private_key:
        # Test authentication
        auth_success = await trader.test_authentication()
        
        if auth_success:
            print("\n✅ CDP v2 authentication successful!")
            
            # Get wallets and balances
            wallets = await trader.get_wallets()
            
            if wallets:
                # Test small trade
                await trader.test_small_trade()
            else:
                print("❌ No wallets found")
        else:
            print("\n❌ CDP v2 authentication failed")
    else:
        print("\n❌ Private key loading failed")

if __name__ == "__main__":
    # Install required package
    try:
        import jwt
        import cryptography
    except ImportError:
        print("Installing required packages...")
        os.system("pip install PyJWT cryptography")
        
    asyncio.run(main()) 