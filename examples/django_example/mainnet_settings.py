"""
Django settings for BSV Middleware - MAINNET Configuration

⚠️ 重要な警告:
このファイルは実際の BSV Mainnet を使用します。
実際のコインとトランザクション手数料が発生します。

セキュリティ要件:
- 秘密鍵を厳重に管理してください
- 環境変数を使用した秘密鍵管理を推奨
- 本番環境では適切なアクセス制御を実施
- ログに秘密鍵を出力しないでください
"""

import os
import json
from pathlib import Path
from myproject.settings import *  # noqa

# ロギング設定をMainnet用にカスタマイズ
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'mainnet': {
            'format': '[MAINNET] {levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'mainnet',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',  # Mainnetではデバッグログを抑制
    },
    'loggers': {
        'bsv_middleware': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Mainnet用のpy-sdk設定
from bsv.keys import PrivateKey
from bsv.wallet.wallet_impl import WalletImpl
from bsv.constants import Network

# Mainnetウォレット設定の読み込み（サーバー用）
mainnet_wallet_config_path = Path(__file__).parent.parent.parent / "examples" / "testnet_setup" / "mainnet_server_wallet_config.json"

if not mainnet_wallet_config_path.exists():
    raise FileNotFoundError(
        f"Mainnet server wallet config not found: {mainnet_wallet_config_path}\n"
        f"Please create a mainnet server wallet first:\n"
        f"  python examples/testnet_setup/create_mainnet_wallet.py"
    )

with open(mainnet_wallet_config_path, 'r') as f:
    mainnet_config = json.load(f)

if mainnet_config.get('network') != 'mainnet':
    raise ValueError(
        f"This wallet is for {mainnet_config.get('network')}, not mainnet.\n"
        f"Please create a mainnet wallet."
    )

# WIF形式の秘密鍵からPrivateKeyオブジェクトを作成
mainnet_private_key = PrivateKey(mainnet_config['private_key'], network=Network.MAINNET)

# WhatsOnChain を有効化 (Mainnet用)
os.environ['USE_WOC'] = '1'

# Mainnet WalletImplを作成
mainnet_wallet = WalletImpl(
    private_key=mainnet_private_key,
    permission_callback=lambda action: True,  # 本番環境では適切な権限確認を実装してください
    load_env=False
)

print(f"✅ Mainnet wallet loaded: {mainnet_config['address']}")


def calculate_request_price_mainnet(request):
    """
    Mainnet用のリクエスト価格計算
    
    ⚠️ Mainnetでは実際のコストを反映した価格設定が重要です
    """
    # パスベースの価格設定
    if request.path == '/premium/':
        return 1000  # 1000 satoshis (約 $0.0005 at $50/BSV)
    elif request.path == '/decorator-payment/':
        return 500   # 500 satoshis
    elif request.path == '/hello-bsv/':
        return 500   # 500 satoshis
    
    # デフォルト: 無料
    return 0


# BSV Middleware設定
BSV_MIDDLEWARE = {
    'WALLET': mainnet_wallet,
    'ALLOW_UNAUTHENTICATED': False,  # Require authentication for testing
    'REQUIRE_AUTH': True,             # 認証必須
    'CALCULATE_REQUEST_PRICE': calculate_request_price_mainnet,
    'LOG_LEVEL': 'info',  # Mainnetではデバッグログを抑制
}

# Django Middleware設定
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',  # API用途では無効化
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # BSV Middleware (リファクタリング後のパス)
    'django_adapter.auth_middleware.BSVAuthMiddleware',      # 認証ミドルウェア
    'django_adapter.payment_middleware.BSVPaymentMiddleware', # 支払いミドルウェア
]

# セキュリティ設定 (本番環境向け)
DEBUG = False  # Mainnetでは必ずFalseに設定
ALLOWED_HOSTS = ['localhost', '127.0.0.1']  # 本番環境では適切なドメインを設定

# HTTPS設定 (本番環境では必須)
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_HSTS_SECONDS = 31536000

# セキュリティヘッダー
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# X_FRAME_OPTIONS = 'DENY'

print("=" * 80)
print("⚠️  MAINNET CONFIGURATION LOADED")
print("=" * 80)
print(f"Network: MAINNET (実際のBSV)")
print(f"Address: {mainnet_config['address']}")
print(f"Debug: {DEBUG}")
print(f"Auth Required: {BSV_MIDDLEWARE['REQUIRE_AUTH']}")
print()
print("⚠️  警告:")
print("  - 実際のBSVを使用します")
print("  - トランザクション手数料が発生します")
print("  - 適切なセキュリティ対策を実施してください")
print("=" * 80)











