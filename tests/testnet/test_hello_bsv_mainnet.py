# """
# BSV Mainnet Authentication + Payment Integration Test

# ⚠️ WARNING: This test uses REAL BSV on Mainnet!
# - Real coins will be spent
# - Transaction fees will be incurred
# - Make sure you understand the costs before running

# This test performs a complete authentication + payment flow on Mainnet:
# 1. Start Django server with Mainnet settings
# 2. Perform authentication handshake
# 3. Send authenticated request with payment
# 4. Receive "Hello BSV" response
# """

# import os
# import sys
# import json
# import time
# import secrets
# import subprocess
# from pathlib import Path
# from typing import Optional, Dict, Any

# # Note: This script doesn't need Django setup since it uses requests library
# # to make actual HTTP requests to a running Django server

# # py-sdk imports
# try:
#     from bsv.keys import PrivateKey, PublicKey
#     from bsv.wallet.wallet_impl import WalletImpl
#     from bsv.constants import Network
#     from bsv.script.type import P2PKH
#     from bsv.auth.peer import Peer, CounterpartyType
# except ImportError as e:
#     print(f"❌ Error: py-sdk not installed or missing components: {e}")
#     print("Please install py-sdk with auth support")
#     sys.exit(1)

# # Middleware imports
# from examples.django_example.django_adapter.transport import DjangoTransport
# from bsv_middleware.wallet_adapter import WalletImplAdapter


# def load_mainnet_wallet(config_name: str = "mainnet_server_wallet_config.json") -> tuple:
#     """Load Mainnet wallet configuration"""
#     config_path = Path(__file__).parents[2] / "examples" / "testnet_setup" / config_name
    
#     if not config_path.exists():
#         print(f"❌ Error: Mainnet wallet not found: {config_path}")
#         print()
#         print("Create a Mainnet wallet:")
#         print("   python examples/testnet_setup/create_mainnet_wallet.py")
#         sys.exit(1)
    
#     with open(config_path, 'r') as f:
#         config = json.load(f)
    
#     if config.get('network') != 'mainnet':
#         print(f"❌ Error: This wallet is for {config.get('network')}, not mainnet")
#         sys.exit(1)
    
#     # Restore private key from WIF
#     private_key = PrivateKey(config['private_key'], network=Network.MAINNET)
    
#     # Enable WhatsOnChain for mainnet
#     os.environ['USE_WOC'] = '1'
    
#     wallet = WalletImpl(
#         private_key=private_key,
#         permission_callback=lambda action: True,
#         load_env=False
#     )
    
#     return wallet, config


# def check_balance(wallet, wallet_config) -> Optional[int]:
#     """Check wallet balance"""
#     print()
#     print("=" * 80)
#     print("💰 Balance Check (Mainnet)")
#     print("=" * 80)
    
#     try:
#         # Get UTXOs from WhatsOnChain
#         utxos = wallet._get_utxos_from_woc(wallet_config['address'])
        
#         if not utxos or (len(utxos) == 1 and 'error' in utxos[0]):
#             print()
#             print(f"❌ Error: No balance in this wallet")
#             print(f"   Address: {wallet_config['address']}")
#             print()
#             print("Next steps:")
#             print(f"  1. Send some BSV to this address")
#             print(f"  2. Check on WhatsOnChain: https://whatsonchain.com/address/{wallet_config['address']}")
#             print(f"  3. Wait for confirmation, then re-run this test")
#             return None
        
#         total_balance = sum(utxo.get('satoshis', 0) for utxo in utxos)
#         print(f"✅ Balance: {total_balance:,} satoshis ({total_balance / 100000000:.8f} BSV)")
#         print(f"   UTXOs: {len(utxos)}")
#         return total_balance
        
#     except Exception as e:
#         print(f"⚠️  Balance check error: {e}")
#         return None


# def build_general_message_payload(
#     request_id: str,
#     method: str,
#     url: str,
#     headers: Dict[str, str],
#     body: bytes = b''
# ) -> bytes:
#     """
#     Build General Message payload (BRC-104 format, matching TypeScript implementation)
    
#     Format (matching auth-express-middleware buildAuthMessageFromRequest):
#     - Request ID (base64 decoded bytes)
#     - Method (VarInt length + UTF-8 bytes)
#     - Pathname (VarInt length + UTF-8 bytes, or -1)
#     - Search (VarInt length + UTF-8 bytes, or -1)
#     - Headers count (VarInt)
#     - For each header:
#       - Key (VarInt length + UTF-8 bytes)
#       - Value (VarInt length + UTF-8 bytes)
#     - Body (VarInt length + raw bytes, or -1)
#     """
#     import base64
#     from urllib.parse import urlparse
    
#     def encode_varint(n: int) -> bytes:
#         """
#         Encode integer as VarInt (matching TypeScript SDK)
#         Negative numbers are converted using 2's complement (add 2^64)
#         """
#         if n == -1:
#             # TypeScript: -1 becomes 2^64 - 1 = 0xFFFFFFFFFFFFFFFF
#             # Encoded as: 0xff followed by 8 bytes of 0xff
#             return bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
#         if n < 0:
#             # Handle other negative numbers using 2's complement
#             n = n + (2 ** 64)
        
#         if n < 0xfd:
#             return bytes([n])
#         elif n <= 0xffff:
#             return b'\xfd' + n.to_bytes(2, 'little')
#         elif n <= 0xffffffff:
#             return b'\xfe' + n.to_bytes(4, 'little')
#         else:
#             return b'\xff' + n.to_bytes(8, 'little')
    
#     def encode_string(s: str) -> bytes:
#         """Encode string with VarInt length prefix"""
#         s_bytes = s.encode('utf-8')
#         return encode_varint(len(s_bytes)) + s_bytes
    
#     payload = b''
    
#     # 1. Request ID (base64 decoded)
#     request_id_bytes = base64.b64decode(request_id)
#     payload += request_id_bytes
    
#     # 2. Method
#     payload += encode_string(method)
    
#     # 3. Parse URL into pathname and search
#     parsed = urlparse(url)
    
#     # Pathname
#     if parsed.path:
#         payload += encode_string(parsed.path)
#     else:
#         payload += encode_varint(-1)
    
#     # Search (query string with ?)
#     if parsed.query:
#         search_with_question = '?' + parsed.query
#         payload += encode_string(search_with_question)
#     else:
#         payload += encode_varint(-1)
    
#     # 4. Headers (filtered and sorted)
#     # Include only headers that match TypeScript logic:
#     # - x-bsv-* (but not x-bsv-auth-*)
#     # - content-type (normalized)
#     # - authorization
#     filtered_headers = []
#     for key, value in headers.items():
#         key_lower = key.lower()
#         # Normalize content-type by removing parameters
#         if key_lower == 'content-type':
#             value = value.split(';')[0].strip()
#         # Include matching headers
#         if (key_lower.startswith('x-bsv-') and not key_lower.startswith('x-bsv-auth-')) or \
#            key_lower in ['content-type', 'authorization']:
#             filtered_headers.append((key_lower, value))
    
#     # Sort by key
#     filtered_headers.sort(key=lambda x: x[0])
    
#     payload += encode_varint(len(filtered_headers))
#     for key, value in filtered_headers:
#         payload += encode_string(key)
#         payload += encode_string(value)
    
#     # 5. Body
#     if body:
#         payload += encode_varint(len(body))
#         payload += body
#     else:
#         payload += encode_varint(-1)
    
#     return payload


# def test_mainnet_auth_payment():
#     """
#     Mainnet Authentication + Payment Integration Test
    
#     ⚠️ WARNING: Uses REAL BSV on Mainnet!
#     """
#     print()
#     print("=" * 80)
#     print("🌐 BSV Mainnet Authentication + Payment Integration Test")
#     print("=" * 80)
#     print()
#     print("⚠️  This test uses REAL BSV on Mainnet!")
#     print("   - Real coins will be spent")
#     print("   - Transaction fees will be incurred")
#     print("   - Estimated cost: ~1,000 satoshis ($0.0005 at $50/BSV)")
#     print()
    
#     confirm = input("Do you want to proceed with Mainnet testing? (yes/no): ").strip().lower()
#     if confirm != 'yes':
#         print("Test cancelled.")
#         sys.exit(0)
    
#     # Load server wallet
#     print("\n📋 Loading server wallet...")
#     server_wallet, server_config = load_mainnet_wallet("mainnet_server_wallet_config.json")
#     print(f"✅ Server wallet loaded")
#     print(f"   Address: {server_config['address']}")
    
#     # Check if client wallet exists
#     client_config_path = Path(__file__).parents[2] / "examples" / "testnet_setup" / "mainnet_client_wallet_config.json"
    
#     if not client_config_path.exists():
#         print()
#         print("=" * 80)
#         print("⚠️  Client wallet not found")
#         print("=" * 80)
#         print()
#         print("To avoid loopback detection, we need a separate client wallet.")
#         print()
#         create_client = input("Create a new client wallet now? (yes/no): ").strip().lower()
        
#         if create_client != 'yes':
#             print()
#             print("Please create a client wallet manually:")
#             print("   python examples/testnet_setup/create_mainnet_wallet.py")
#             print("   (Save as mainnet_client_wallet_config.json)")
#             sys.exit(1)
        
#         # Create client wallet
#         print("\n🔨 Creating client wallet...")
#         from bsv.keys import PrivateKey
#         from bsv.constants import Network
#         from datetime import datetime
        
#         client_private_key_obj = PrivateKey()
#         client_wallet_temp = WalletImpl(
#             private_key=client_private_key_obj,
#             permission_callback=lambda action: True,
#             load_env=False
#         )
        
#         client_config = {
#             "network": "mainnet",
#             "private_key": client_private_key_obj.wif(network=Network.MAINNET),
#             "public_key": client_private_key_obj.public_key().hex(),
#             "address": client_private_key_obj.address(network=Network.MAINNET),
#             "created_at": datetime.now().isoformat()
#         }
        
#         with open(client_config_path, 'w') as f:
#             json.dump(client_config, f, indent=2)
        
#         os.chmod(client_config_path, 0o600)
        
#         print(f"✅ Client wallet created: {client_config_path}")
#         print(f"   Address: {client_config['address']}")
#         print()
#         print("=" * 80)
#         print("💰 Fund the client wallet")
#         print("=" * 80)
#         print()
#         print(f"Send some BSV to: {client_config['address']}")
#         print()
#         print("Recommended amount: 10,000 - 50,000 satoshis")
#         print()
#         print("After funding, press Enter to continue...")
#         input()
    
#     # Load client wallet
#     print("\n📋 Loading client wallet...")
#     client_wallet, client_config = load_mainnet_wallet("mainnet_client_wallet_config.json")
#     print(f"✅ Client wallet loaded")
#     print(f"   Address: {client_config['address']}")
    
#     # Check balances
#     server_balance = check_balance(server_wallet, server_config)
#     if server_balance is None or server_balance < 1000:
#         print("\n❌ Server wallet has insufficient balance")
#         sys.exit(1)
    
#     client_balance = check_balance(client_wallet, client_config)
#     if client_balance is None or client_balance < 1000:
#         print("\n❌ Client wallet has insufficient balance")
#         sys.exit(1)
    
#     # Check if Django server is running
#     print()
#     print("=" * 80)
#     print("🌐 Django Server Check")
#     print("=" * 80)
#     print()
#     print("Make sure Django server is running with Mainnet settings:")
#     print()
#     print("   cd py-middleware/examples/django_example")
#     print("   python manage.py runserver --settings=mainnet_settings")
#     print()
#     print("Server should be running on: http://localhost:8000")
#     print()
    
#     server_ready = input("Is the Django server running? (yes/no): ").strip().lower()
#     if server_ready != 'yes':
#         print("\nPlease start the Django server first, then re-run this test.")
#         sys.exit(0)
    
#     # Test authentication + payment flow
#     print()
#     print("=" * 80)
#     print("🔐 Authentication + Payment Flow Test")
#     print("=" * 80)
    
#     try:
#         import requests
        
#         # Step 1: Initial Message (Authentication handshake)
#         print("\n📤 Step 1: Sending Initial Message...")
        
#         # Get identity keys (public keys) for authentication
#         client_identity_result = client_wallet.get_public_key(None, {'identityKey': True}, "auth_test")
#         server_identity_result = server_wallet.get_public_key(None, {'identityKey': True}, "auth_test")
        
#         client_identity_key = client_identity_result.get('publicKey') or client_identity_result.get('public_key')
#         server_identity_key = server_identity_result.get('publicKey') or server_identity_result.get('public_key')
        
#         print(f"   Client Identity Key: {client_identity_key[:40]}...")
#         print(f"   Server Identity Key: {server_identity_key[:40]}...")
        
#         # Create client Peer
#         client_transport = DjangoTransport(WalletImplAdapter(client_wallet))
#         client_peer = Peer(
#             wallet=WalletImplAdapter(client_wallet),
#             transport=client_transport
#         )
#         client_peer.start()
        
#         # Initial Message
#         initial_nonce = secrets.token_hex(32)  # Save nonce for later use as request_id
#         initial_message_data = {
#             "version": "0.1",  # py-sdk expects "0.1"
#             "messageType": "initialRequest",  # Use snake_case or will be converted
#             "identityKey": client_identity_key,
#             "nonce": initial_nonce,
#             "timestamp": int(time.time() * 1000)
#         }
        
#         initial_response = requests.post(
#             "http://localhost:8000/.well-known/auth",
#             json=initial_message_data,
#             headers={"Content-Type": "application/json"}
#         )
#         print (f"   [DEBUG] Initial response: {initial_response.json()}")
#         print(f"   Response: {initial_response.status_code}")
        
#         if initial_response.status_code != 200:
#             print(f"❌ Initial Message failed: {initial_response.text}")
#             sys.exit(1)
        
#         initial_response_data = initial_response.json()
#         print(f"✅ Initial Message successful")
        
#         # Get server's nonce from initial response
#         server_nonce = initial_response_data.get('nonce', '')
        
#         # Step 2: General Message (Authenticated request with payment)
#         print("\n📤 Step 2: Sending authenticated request with payment...")
        
#         payment_amount = 500  # satoshis
#         target_url = "http://localhost:8000/hello-bsv/"
        
#         # Create payment transaction
#         recipient_address = server_config['address']
#         locking_script = P2PKH().lock(recipient_address)
#         locking_script_hex = locking_script.hex()
        
#         action_args = {
#             "description": f"Mainnet auth+payment test - {payment_amount} sats",
#             "outputs": [{
#                 "satoshis": payment_amount,
#                 "lockingScript": locking_script_hex,
#                 "outputDescription": "Mainnet Hello BSV test"
#             }]
#         }
        
#         print(f"   Creating transaction: {payment_amount} satoshis")
#         create_result = client_wallet.create_action(None, action_args, "mainnet_hello_bsv_test")
#         tx_bytes = create_result['signableTransaction']['tx']
        
#         print(f"   Broadcasting transaction...")
#         internalize_result = client_wallet.internalize_action(None, {"tx": tx_bytes}, "mainnet_hello_bsv_test")
        
#         txid = internalize_result.get('txid')
#         if isinstance(txid, bytes):
#             txid = txid.hex()
        
#         if not txid:
#             print(f"❌ Transaction broadcast failed: {internalize_result.get('error', 'Unknown error')}")
#             sys.exit(1)
        
#         print(f"✅ Transaction broadcast successful")
#         print(f"   TXID: {txid}")
        
#         # Generate general nonce first (needed for signature)
#         import base64
#         import os as _os
#         general_nonce_bytes = _os.urandom(32)
#         general_nonce = base64.b64encode(general_nonce_bytes).decode('ascii')
        
#         # Prepare payment header (reuse for signing and HTTP request)
#         payment_header_value = json.dumps({
#             "satoshis": payment_amount,
#             "tx": tx_bytes.hex(),
#             "derivationPrefix": "m/0",
#             "derivationSuffix": "0"
#         })
        
#         # Build General Message payload (matching TypeScript implementation)
#         request_headers_for_signature = {
#             "Content-Type": "application/json",
#             "X-BSV-Payment": payment_header_value,
#         }
        
#         # Convert initial_nonce hex to base64 for request_id
#         request_id_base64 = base64.b64encode(bytes.fromhex(initial_nonce)).decode('ascii')
        
#         payload = build_general_message_payload(
#             request_id=request_id_base64,
#             method="GET",
#             url=target_url,
#             headers=request_headers_for_signature,
#             body=b''
#         )
        
#         # Debug: log payload digest for comparison with server
#         import hashlib
#         payload_digest = hashlib.sha256(payload).digest()
#         print(f"   [DEBUG] Client payload digest: {payload_digest.hex()[:64]}")
#         print(f"   [DEBUG] Client payload length: {len(payload)} bytes")
        
#         # Sign the payload (BRC-100 compliant flat structure with Python snake_case)
#         # key_id format must match Peer expectation: "{client_nonce} {server_nonce}" (both base64)
#         key_id = f"{general_nonce} {server_nonce}"
        
#         # Extra debug: show nonces, key_id and protocol used
#         print(f"   [DEBUG] Nonces: client(general)={general_nonce}, server={server_nonce}")
#         print(f"   [DEBUG] key_id: {key_id[:64]}...")
#         print(f"   [DEBUG] protocol_id: [2, 'auth message signature']")
        
#         signature_result = client_wallet.create_signature(
#             None,
#             {
#                 "data": payload,  # bytes data
#                 "protocol_id": [2, "auth message signature"],  # Must match server Peer
#                 "key_id": key_id,
#                 "counterparty": server_identity_key  # Server's identity key
#             },
#             "mainnet_auth_test"
#         )
#         print(f"   [DEBUG] Signature result: {signature_result}")
#         # Handle different possible return formats
#         if 'error' in signature_result:
#             print(f"❌ Signature creation failed: {signature_result['error']}")
#             sys.exit(1)
        
#         signature = signature_result.get('signature')
#         if not signature:
#             print(f"❌ No signature returned: {signature_result}")
#             sys.exit(1)
        
#         # Convert signature to hex if it's bytes
#         if isinstance(signature, bytes):
#             signature_hex = signature.hex()
#         else:
#             signature_hex = signature

#             print()
#             print("📊 Transaction Details:")
#             print(f"   TXID: {txid}")
#             print(f"   Amount: {payment_amount} satoshis")
#             print(f"   WhatsOnChain: https://whatsonchain.com/tx/{txid}")
#             print()
#             print("=" * 80)
#             print()
#             print("💡 Next steps:")
#             print("   1. Verify transaction on WhatsOnChain")
#             print("   2. Check server logs for authentication details")
#             print("   3. Test with different payment amounts")
#             print()
            

        
#     except Exception as e:
#         print(f"\n❌ Error during test: {e}")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)


# if __name__ == "__main__":
#     test_mainnet_auth_payment()

