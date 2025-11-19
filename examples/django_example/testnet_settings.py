"""
Django settings for BSV middleware example project - TESTNET VERSION

このファイルは、testnet環境でdjango_exampleを実行するための設定です。

使用方法:
    python manage.py runserver --settings=testnet_settings
"""

import os
import json
from pathlib import Path
from typing import Dict, Any

# 通常の設定をインポート
from myproject.settings import *

# ===== TESTNET SPECIFIC SETTINGS =====

print("=" * 70)
print("🔧 Loading TESTNET configuration...")
print("=" * 70)

# Testnetウォレット設定の読み込み
# django_example/ -> examples/ -> py-middleware/ -> examples/testnet_setup/
TESTNET_WALLET_CONFIG_PATH = Path(__file__).parent.parent.parent / "examples" / "testnet_setup" / "testnet_wallet_config.json"

if not TESTNET_WALLET_CONFIG_PATH.exists():
    print()
    print("❌ Testnet wallet config not found!")
    print(f"   Expected at: {TESTNET_WALLET_CONFIG_PATH}")
    print()
    print("Please create a testnet wallet first:")
    print("  cd examples/testnet_setup")
    print("  python create_testnet_wallet.py")
    print()
    raise FileNotFoundError(f"Testnet wallet config not found: {TESTNET_WALLET_CONFIG_PATH}")

# ウォレット設定を読み込む
with open(TESTNET_WALLET_CONFIG_PATH, 'r') as f:
    testnet_wallet_config = json.load(f)

print(f"✅ Loaded testnet wallet config")
print(f"   Address: {testnet_wallet_config['address']}")
print(f"   Network: testnet")

# py-sdkのウォレットを作成
try:
    from bsv.wallet.wallet_impl import WalletImpl
    from bsv.keys import PrivateKey
    from bsv.constants import Network
    
    # WIF から秘密鍵を復元
    private_key_obj = PrivateKey(
        testnet_wallet_config["private_key"], 
        network=Network.TESTNET
    )
    
    # WhatsOnChainから実際のUTXOを取得するように設定
    os.environ['USE_WOC'] = '1'
    
    # ウォレット作成
    testnet_wallet = WalletImpl(
        private_key=private_key_obj,
        permission_callback=lambda action: True,  # 全ての操作を自動許可
        load_env=False
    )
    
    print(f"✅ Created testnet WalletImpl")
    
except Exception as e:
    print(f"❌ Failed to create testnet wallet: {e}")
    print("   Using mock wallet instead")
    
    # Fallback: モックウォレット
    class TestnetMockWallet:
        """Testnet mock wallet for demonstration."""
        
        def sign_message(self, message: bytes) -> bytes:
            return b'testnet_mock_signature'
        
        def get_public_key(self) -> str:
            return testnet_wallet_config.get('public_key', 'mock_public_key')
        
        def internalize_action(self, action: dict) -> dict:
            return {
                'accepted': True,
                'satoshisPaid': action.get('satoshis', 0),
                'transactionId': 'testnet_mock_tx_id'
            }
    
    testnet_wallet = TestnetMockWallet()

# 証明書受信ハンドラー
def handle_certificates_received_testnet(sender_public_key, certificates, request, response):
    """Handle received certificates in testnet."""
    print(f"[TESTNET] Received {len(certificates)} certificates from {sender_public_key}")
    for cert in certificates:
        print(f"[TESTNET] Certificate type: {getattr(cert, 'type', 'unknown')}")

# 価格計算関数（testnet用）
def calculate_request_price_testnet(request):
    """Calculate the price for a request (testnet)."""
    # Free endpoints
    if request.path.startswith('/free/'):
        return 0
    
    # Public endpoints
    if request.path in ['/public/', '/health/', '/']:
        return 0
    
    # Test endpoint
    if request.path == '/test/':
        return 0
    
    # Protected endpoints (require auth + small payment for testnet)
    if request.path == '/protected/':
        return 100  # Small amount for testnet testing
    
    # Premium endpoints (require auth + larger payment)
    if request.path == '/premium/':
        return 500  # Moderate amount for testnet
    
    if request.path == '/decorator-payment/':
        return 300
    
    # Default: free
    return 0

# BSV Middleware Configuration (TESTNET)
BSV_MIDDLEWARE = {
    # Testnet wallet
    'WALLET': testnet_wallet,
    
    # Testnet環境では認証を緩く設定
    'ALLOW_UNAUTHENTICATED': False,  # テスト用に認証なしも許可
    'REQUIRE_AUTH': False,  # 支払いのみでもOK（テスト用）
    
    # Price calculation
    'CALCULATE_REQUEST_PRICE': calculate_request_price_testnet,
    
    # Certificate requests (optional for testnet)
    'CERTIFICATE_REQUESTS': None,  # Testnetでは証明書リクエストをスキップ
    
    # Certificate handler
    'ON_CERTIFICATES_RECEIVED': handle_certificates_received_testnet,
    
    # Logging
    'LOG_LEVEL': 'debug',
}

# Middleware configuration for testnet
# 認証をオプショナルにするため、AuthMiddlewareをコメントアウトすることも可能
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # BSV Middleware (Testnet configuration)
    # Note: AuthMiddlewareをコメントアウトすると支払いのみのテストが可能
    # 'bsv_middleware.django.auth_middleware.BSVAuthMiddleware',
    'bsv_middleware.django.payment_middleware.BSVPaymentMiddleware',
]

# CORS設定（テスト用）
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Logging configuration (more verbose for testnet)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[TESTNET] {levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'bsv_middleware': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

print()
print("=" * 70)
print("✅ Testnet configuration loaded successfully")
print("=" * 70)
print()
print("Configuration:")
print(f"  - Wallet Address: {testnet_wallet_config['address']}")
print(f"  - Network: testnet")
print(f"  - Auth Required: {BSV_MIDDLEWARE.get('REQUIRE_AUTH', True)}")
print(f"  - Allow Unauth: {BSV_MIDDLEWARE.get('ALLOW_UNAUTHENTICATED', False)}")
print()
print("Pricing:")
print(f"  - /protected/: 100 satoshis")
print(f"  - /premium/: 500 satoshis")
print(f"  - /decorator-payment/: 300 satoshis")
print()
print("To start the server:")
print("  python manage.py runserver --settings=testnet_settings")
print()
print("=" * 70)

