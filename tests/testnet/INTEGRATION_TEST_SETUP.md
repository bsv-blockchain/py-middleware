# 認証 + 支払い統合テストのセットアップガイド

## 🎯 テストの目的

実際のミドルウェアエンドポイントで、BSV 認証 + 支払いの完全なフローを testnet でテストする。

---

## 📦 必要な環境コンポーネント

### 1. **ウォレット環境**

#### ✅ 既に準備済み：

```bash
# Testnetウォレット（クライアント用）
/py-middleware/examples/testnet_setup/testnet_wallet_config.json
```

#### 🔧 追加で必要（オプション）：

```bash
# サーバー用ウォレット（自己認証の場合は不要）
# 同じウォレットでクライアント/サーバー両方を兼ねることも可能
```

### 2. **ネットワーク環境**

```
testnet blockchain
├── WhatsOnChain API（UTXO取得、トランザクション確認）
├── ARC/WOC Broadcaster（トランザクション送信）
└── testnet faucet（コイン取得）
```

---

## 🏗️ テストアーキテクチャの選択肢

### **Option A: RequestFactory（単体テスト的）**

```python
# メリット：高速、簡単
# デメリット：実際のHTTPではない

client_wallet = load_testnet_wallet()
server_wallet = client_wallet  # 自己認証

# ミドルウェアを手動で適用
auth_middleware = BSVAuthMiddleware(...)
payment_middleware = BSVPaymentMiddleware(...)

request = factory.get('/premium/')
request = auth_middleware.process_request(request)
response = payment_middleware(request)
```

**必要なセットアップ：**

- [x] testnet ウォレット
- [x] Django settings
- [ ] ミドルウェア設定
- [ ] 手動でのミドルウェアチェーン構築

---

### **Option B: Django Live Server（統合テスト - 推奨）**

```python
# メリット：実際のHTTP、完全なフロー
# デメリット：遅い、複雑

import requests
from django.test import LiveServerTestCase

class TestAuthPaymentIntegration(LiveServerTestCase):
    def setUp(self):
        # サーバーが自動起動される
        self.server_url = self.live_server_url

    def test_full_flow(self):
        # 1. 認証フロー
        auth_response = requests.get(
            f"{self.server_url}/.well-known/auth",
            headers={"x-bsv-identity": client_identity}
        )

        # 2. 支払いフロー
        payment_response = requests.post(
            f"{self.server_url}/premium/",
            headers={
                "x-bsv-auth": auth_token,
                "x-bsv-payment": payment_data
            }
        )
```

**必要なセットアップ：**

1. **Django アプリケーション設定**

```python
# settings.py
MIDDLEWARE = [
    'bsv_middleware.django.auth_middleware.BSVAuthMiddleware',
    'bsv_middleware.django.payment_middleware.BSVPaymentMiddleware',
]

BSV_MIDDLEWARE = {
    'WALLET': server_wallet,
    'CALCULATE_REQUEST_PRICE': lambda req: 500,
    'REQUIRE_AUTH': True,  # 認証必須
}
```

2. **URL 設定**

```python
# urls.py
urlpatterns = [
    path('.well-known/bsv/auth', auth_endpoint),
    path('premium/', premium_endpoint),
]
```

3. **エンドポイント実装**

```python
def premium_endpoint(request):
    # 認証とpaymentの両方がミドルウェアで検証済み
    return JsonResponse({
        'message': 'Premium content',
        'identity': request.auth.identity_key,
        'payment': request.payment.satoshis_paid
    })
```

---

### **Option C: py-sdk Peer（最も本格的）**

```python
# メリット：完全なBSV認証プロトコル
# デメリット：最も複雑

from bsv.auth.peer import Peer

# クライアント側
client_peer = Peer(client_wallet)

# サーバー側
server_peer = Peer(server_wallet)

# 相互認証
auth_result = await client_peer.authenticate_with_server(
    server_url="http://localhost:8000"
)

# 支払い付きリクエスト
response = await client_peer.fetch_with_payment(
    url="http://localhost:8000/premium/",
    satoshis=500
)
```

**必要なセットアップ：**

- [x] py-sdk with Peer support
- [ ] サーバー側の Peer エンドポイント
- [ ] 非同期対応
- [ ] 証明書管理

---

## 🚀 推奨セットアップ（段階的アプローチ）

### **Phase 1: 支払いのみ（✅ 完了）**

```
クライアント → [PaymentMiddleware] → エンドポイント
```

- 認証なし
- 支払い検証のみ
- testnet でトランザクション送信

**現在のテスト：** `test_middleware_endpoint_testnet.py`

---

### **Phase 2: 認証のみ**

```
クライアント → [AuthMiddleware] → エンドポイント
```

- 支払いなし
- 認証検証のみ
- 証明書のリクエスト/検証

**必要な追加実装：**

```python
# test_auth_only_testnet.py

def test_auth_flow():
    # 1. /.well-known/authにアクセス
    auth_endpoint_response = get_auth_config()

    # 2. 認証ヘッダーを作成
    auth_header = create_auth_header(
        identity_key=client_public_key,
        signature=sign_message(...)
    )

    # 3. 保護されたエンドポイントにアクセス
    response = requests.get(
        '/protected/',
        headers={'x-bsv-auth': auth_header}
    )

    assert response.status_code == 200
```

---

### **Phase 3: 認証 + 支払い（完全統合）**

```
クライアント → [AuthMiddleware] → [PaymentMiddleware] → エンドポイント
```

- 両方のミドルウェアを使用
- 完全なエンドツーエンドフロー

**推奨テスト構成：**

```python
# test_full_integration_testnet.py

class TestFullIntegration:
    """認証 + 支払いの完全統合テスト"""

    @pytest.fixture
    def setup_server(self):
        """Django Live Serverをセットアップ"""
        # Option: LiveServerTestCaseを使用
        # または手動でDjango dev serverを起動
        pass

    def test_01_auth_then_payment(self):
        """完全なフロー：認証 → 支払い → アクセス"""

        # Step 1: 認証フロー
        auth_result = authenticate_with_server(
            server_url=self.server_url,
            client_wallet=self.wallet
        )
        auth_token = auth_result['token']

        # Step 2: 支払いトランザクション作成
        payment_tx = create_payment_transaction(
            wallet=self.wallet,
            amount=500
        )

        # Step 3: 両方のヘッダー付きでリクエスト
        response = requests.get(
            f"{self.server_url}/premium/",
            headers={
                'x-bsv-auth': auth_token,
                'x-bsv-payment': json.dumps({
                    'transaction': payment_tx.hex(),
                    'derivationPrefix': '...',
                    'derivationSuffix': '...'
                })
            }
        )

        # Step 4: 検証
        assert response.status_code == 200
        data = response.json()
        assert 'identity_key' in data
        assert 'payment_info' in data
        assert data['payment_info']['satoshis_paid'] >= 500
```

---

## 📝 実装の優先順位

### ✅ **現在完了：**

1. [x] Phase 1: 支払いのみのテスト
2. [x] testnet トランザクション送信
3. [x] ミドルウェア検証

### 🚧 **次のステップ（推奨順）：**

1. **認証エンドポイントの実装**

   ```python
   # urls.py に追加
   path('.well-known/bsv/auth', auth_config_endpoint)
   ```

2. **認証のみのテスト作成**

   - RequestFactory ベースでシンプルに開始
   - 認証ヘッダーの作成と検証

3. **Live Server 統合テストの作成**

   - Django LiveServerTestCase を使用
   - 実際の HTTP リクエスト

4. **完全統合テスト**
   - 認証 + 支払い
   - エンドツーエンド

---

## 🔧 必要な設定ファイル

### 1. **テスト用 Django 設定**

```python
# tests/testnet_settings.py

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'bsv_middleware.django.auth_middleware.BSVAuthMiddleware',
    'bsv_middleware.django.payment_middleware.BSVPaymentMiddleware',
]

BSV_MIDDLEWARE = {
    'WALLET': testnet_wallet,
    'REQUIRE_AUTH': True,  # 認証を有効化
    'CALCULATE_REQUEST_PRICE': lambda req: 500,
    'CERTIFICATES_TO_REQUEST': [...],  # 必要な証明書
}
```

### 2. **テスト用 URL 設定**

```python
# tests/testnet_urls.py

urlpatterns = [
    # 認証エンドポイント
    path('.well-known/bsv/auth', auth_config_view),

    # 保護されたエンドポイント
    path('premium/', premium_view, name='premium'),
    path('protected/', protected_view, name='protected'),
]
```

### 3. **環境変数**

```bash
# .env.testnet
USE_WOC=1
BSV_NETWORK=testnet
DJANGO_SETTINGS_MODULE=tests.testnet_settings
```

---

## 🎯 まとめ：推奨アプローチ

### **現時点で最も実用的な方法：**

**RequestFactory + 両方のミドルウェア**

```python
# 高速、シンプル、十分な検証が可能

def test_auth_and_payment():
    # 1. 認証ミドルウェアを適用
    auth_middleware = BSVAuthMiddleware(...)
    request_with_auth = auth_middleware(request)

    # 2. 支払いミドルウェアを適用
    payment_middleware = BSVPaymentMiddleware(...)
    final_response = payment_middleware(request_with_auth)

    # 3. 検証
    assert final_response.status_code == 200
```

**メリット：**

- サーバー起動不要
- 高速なテスト実行
- testnet での実際のトランザクション送信
- 両方のミドルウェアの動作を検証

**次のステップ：**
このアプローチで認証+支払いテストを作成しますか？


