"""
Django settings for BSV middleware example project - TESTNET FULL VERSION

認証 + 支払いの両方を有効にした完全なテスト設定

使用方法:
    python manage.py runserver --settings=testnet_settings_full
"""

import os
import json
from pathlib import Path

# 通常の設定をインポート
from myproject.settings import *

# ===== TESTNET FULL CONFIGURATION (Auth + Payment) =====

print("=" * 70)
print("🔧 Loading TESTNET FULL configuration (Auth + Payment)...")
print("=" * 70)

# Testnetウォレット設定の読み込み
TESTNET_WALLET_CONFIG_PATH = Path(__file__).parent.parent.parent / "examples" / "testnet_setup" / "testnet_wallet_config.json"

if not TESTNET_WALLET_CONFIG_PATH.exists():
    raise FileNotFoundError(f"Testnet wallet config not found: {TESTNET_WALLET_CONFIG_PATH}")

with open(TESTNET_WALLET_CONFIG_PATH, 'r') as f:
    testnet_wallet_config = json.load(f)

print(f"✅ Loaded testnet wallet config")
print(f"   Address: {testnet_wallet_config['address']}")

# py-sdkのウォレットを作成
try:
    from bsv.wallet.wallet_impl import WalletImpl
    from bsv.keys import PrivateKey
    from bsv.constants import Network
    
    private_key_obj = PrivateKey(
        testnet_wallet_config["private_key"], 
        network=Network.TESTNET
    )
    
    os.environ['USE_WOC'] = '1'
    
    testnet_wallet = WalletImpl(
        private_key=private_key_obj,
        permission_callback=lambda action: True,
        load_env=False
    )
    
    print(f"✅ Created testnet WalletImpl")
    
except Exception as e:
    print(f"❌ Failed to create testnet wallet: {e}")
    raise

# 証明書受信ハンドラー
def handle_certificates_received_testnet(sender_public_key, certificates, request, response):
    """Handle received certificates in testnet."""
    print(f"[TESTNET-FULL] Received {len(certificates)} certificates from {sender_public_key}")

# 価格計算関数
def calculate_request_price_testnet(request):
    """Calculate the price for a request (testnet)."""
    if request.path in ['/public/', '/health/', '/', '/test/']:
        return 0
    
    if request.path == '/protected/':
        return 100
    
    if request.path == '/premium/':
        return 500
    
    if request.path == '/decorator-payment/':
        return 300
    
    if request.path == '/hello-bsv/':
        return 500  # Hello BSV endpoint: 500 satoshis
    
    return 0

# BSV Middleware Configuration (TESTNET FULL - Auth + Payment)
BSV_MIDDLEWARE = {
    # Testnet wallet
    'WALLET': testnet_wallet,
    
    # 認証と支払いの両方を有効化
    'ALLOW_UNAUTHENTICATED': False,  # 認証必須
    'REQUIRE_AUTH': True,            # 認証必須（PaymentMiddleware用）
    
    # Price calculation
    'CALCULATE_REQUEST_PRICE': calculate_request_price_testnet,
    
    # Certificate requests
    'CERTIFICATE_REQUESTS': None,
    
    # Certificate handler
    'ON_CERTIFICATES_RECEIVED': handle_certificates_received_testnet,
    
    # Logging
    'LOG_LEVEL': 'debug',
}

# Middleware configuration (Auth + Payment 両方有効)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # BSV Middleware (両方有効)
    'bsv_middleware.django.auth_middleware.BSVAuthMiddleware',
    'bsv_middleware.django.payment_middleware.BSVPaymentMiddleware',
]

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[TESTNET-FULL] {levelname} {asctime} {module} {message}',
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
print("✅ Testnet FULL configuration loaded successfully")
print("=" * 70)
print()
print("Configuration:")
print(f"  - Wallet Address: {testnet_wallet_config['address']}")
print(f"  - Network: testnet")
print(f"  - Auth Required: {BSV_MIDDLEWARE.get('REQUIRE_AUTH', True)}")
print(f"  - Allow Unauth: {BSV_MIDDLEWARE.get('ALLOW_UNAUTHENTICATED', False)}")
print()
print("Middleware Stack:")
print("  - BSVAuthMiddleware: ENABLED ✅")
print("  - BSVPaymentMiddleware: ENABLED ✅")
print()
print("Pricing:")
print(f"  - /protected/: 100 satoshis")
print(f"  - /premium/: 500 satoshis (Auth + Payment required)")
print(f"  - /decorator-payment/: 300 satoshis")
print()
print("To start the server:")
print("  python manage.py runserver --settings=testnet_settings_full")
print()
print("=" * 70)

