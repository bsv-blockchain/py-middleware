# テストアーキテクチャ: py-sdk vs Middleware

## 🎯 問題の本質

**現在の testnet テストは py-sdk のテストであり、middleware のテストではない**

### **現在の問題**

```python
# tests/testnet/test_auth_flow_testnet.py
def test_01_wallet_initialization(self):
    """Test 1: Testnet ウォレット初期化"""
    assert self.wallet is not None
    assert hasattr(self.wallet, 'get_public_key')
    # ❌ これは py-sdk のテスト（WalletImpl のテスト）
```

これは **middleware のテスト** ではなく、**py-sdk の WalletImpl のテスト** です。

---

## 📊 テストの分類

### **1. py-sdk テスト**

**目的**: py-sdk（bsv-sdk）の機能をテスト

```python
# py-sdk/tests/test_wallet.py (py-sdk のテストスイート)

def test_wallet_creation():
    """WalletImpl の作成テスト"""
    private_key = PrivateKey()
    wallet = WalletImpl(private_key=private_key, ...)
    assert wallet is not None

def test_signature_creation():
    """署名作成のテスト"""
    wallet = WalletImpl(...)
    signature = wallet.create_signature({...})
    assert signature is not None
```

**場所**: `py-sdk/tests/`  
**責任**: py-sdk 開発者

---

### **2. Middleware テスト**

**目的**: Django middleware の統合動作をテスト

```python
# py-middleware/tests/integration/test_middleware_integration.py

def test_authenticated_request():
    """認証付きリクエストの処理（ミドルウェア統合テスト）"""

    # クライアント側（AuthFetch相当）
    client = AuthenticatedClient(wallet)

    # サーバー側（Django + BSVAuthMiddleware）
    response = client.post(
        '/api/protected-endpoint',
        data={'message': 'Hello'}
    )

    # ✅ ミドルウェアを通した統合動作をテスト
    assert response.status_code == 200
    assert response.json()['authenticated'] == True
```

**場所**: `py-middleware/tests/integration/`  
**責任**: py-middleware 開発者

---

## 🎯 TypeScript/Go 版の正しいアプローチ

### **TypeScript 版**

```typescript
// auth-express-middleware/src/__tests/integration.test.ts

test('Test 1: Simple POST request with JSON', async () => {
  // クライアント側（AuthFetch）
  const wallet = new MockWallet(privKey)
  const authFetch = new AuthFetch(wallet)

  // サーバー側（Express + AuthMiddleware）
  const result = await authFetch.fetch(
    'http://localhost:3000/other-endpoint',  // ← Express server with middleware
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ message: 'Hello' })
    }
  )

  // ✅ ミドルウェアの統合動作をテスト
  expect(result.status).toBe(200)
})
```

**テスト内容**:

- ✅ クライアント-サーバー通信
- ✅ 認証ハンドシェイク
- ✅ Middleware の処理
- ✅ レスポンスの検証

### **Go 版**

```go
// go-bsv-middleware/pkg/internal/test/integrationtests/

func TestAuthenticatedRequest(t *testing.T) {
    // サーバー側（Middleware適用済み）
    serverURL, cleanup := fixture.NewServerFixture(t).
        WithMiddleware(authMiddleware).
        WithRoute("/endpoint", handler).
        Started()
    defer cleanup()

    // クライアント側
    client := testClient(wallet)
    resp, err := client.Post(serverURL + "/endpoint", body)

    // ✅ ミドルウェアの統合動作をテスト
    require.NoError(t, err)
    require.Equal(t, 200, resp.StatusCode)
}
```

---

## 📋 現在のテスト構成（2025 年更新）

### **実装済みディレクトリ構造**

```
py-sdk/
└── tests/                           # py-sdk のテスト
    ├── test_wallet.py               # WalletImpl のテスト
    ├── test_keys.py                 # 鍵管理のテスト
    ├── test_signature.py            # 署名のテスト
    └── test_woc.py                  # WhatsOnChain API のテスト

py-middleware/
└── tests/
    ├── integration/                 # ✅ コア統合テスト（TypeScript/Go style）
    │   ├── __init__.py
    │   └── test_middleware_auth.py  # 認証ミドルウェア統合テスト（11テスト）
    │
    ├── compliance/                  # ✅ プロトコル準拠テスト
    │   ├── __init__.py
    │   ├── test_brc_protocol.py     # BRCプロトコル準拠
    │   └── test_express_compatibility.py # Express互換性
    │
    ├── features/                    # ✅ 機能固有テスト
    │   ├── __init__.py
    │   ├── test_multipart_upload.py # マルチパートアップロード
    │   └── test_text_plain_support.py # text/plainサポート
    │
    ├── testnet/                     # ✅ 実ネットワークテスト
    │   ├── __init__.py
    │   ├── README.md
    │   ├── test_auth_flow_testnet.py
    │   ├── test_payment_flow_testnet.py
    │   ├── test_live_server_integration_testnet.py
    │   └── (その他testnetテスト)
    │
    ├── settings.py                  # Django テスト設定
    ├── urls.py                      # Django テストURL
    │
    └── (個別テストファイル)
        ├── test_basic.py            # 基本スモークテスト
        ├── test_bsv_auth_flow.py    # 認証フロー詳細
        ├── test_bsv_payment_flow.py # 支払いフロー詳細
        ├── test_performance.py      # パフォーマンステスト
        ├── test_real_bsv_auth.py    # 実BSV認証テスト
        ├── test_real_bsv_payment.py # 実BSV支払いテスト
        ├── test_code_review_fixes.py # コードレビュー対応
        └── test_django_example_comprehensive.py # Django例アプリ
```

---

## 🔍 各テストレベルの詳細

### **Level 1: Integration Tests（統合テスト）** ← **✅ 実装済み！**

**目的**: ミドルウェアの統合動作をテスト

```python
# tests/integration/test_auth_flow.py

class TestAuthFlow:
    """認証フロー統合テスト（TypeScript/Go方式）"""

    @pytest.fixture
    def setup(self):
        # サーバーセットアップ（Django TestCase）
        self.client = Client()

        # ウォレット作成
        self.wallet = WalletImpl(PrivateKey(), ...)

        # Middleware 設定
        settings.BSV_MIDDLEWARE = {
            'WALLET': self.wallet,
            'ALLOW_UNAUTHENTICATED': False
        }

    def test_authenticated_post_request(self):
        """認証付き POST リクエスト（ミドルウェア統合）"""

        # クライアント側: 認証ヘッダーを生成
        auth_headers = self._create_auth_headers(self.wallet)

        # サーバー側: Middleware を通してリクエスト
        response = self.client.post(
            '/api/protected',
            data={'message': 'Hello'},
            **auth_headers
        )

        # ✅ ミドルウェアの動作を検証
        assert response.status_code == 200
        assert response.json()['authenticated'] == True

    def test_unauthenticated_request_rejected(self):
        """未認証リクエストの拒否（ミドルウェア統合）"""

        # 認証ヘッダーなし
        response = self.client.post('/api/protected', data={})

        # ✅ ミドルウェアが正しく拒否することを検証
        assert response.status_code == 401

    def test_json_request(self):
        """JSON リクエストの処理（TypeScript Test 1 相当）"""
        auth_headers = self._create_auth_headers(self.wallet)

        response = self.client.post(
            '/api/endpoint',
            data=json.dumps({'message': 'Hello'}),
            content_type='application/json',
            **auth_headers
        )

        assert response.status_code == 200

    def test_binary_request(self):
        """バイナリリクエストの処理（TypeScript Test 4 相当）"""
        auth_headers = self._create_auth_headers(self.wallet)

        binary_data = b'Hello from binary!'
        response = self.client.post(
            '/api/endpoint',
            data=binary_data,
            content_type='application/octet-stream',
            **auth_headers
        )

        assert response.status_code == 200
```

**特徴**:

- ✅ **クライアント-サーバー統合動作**をテスト
- ✅ **Middleware の実際の処理**をテスト
- ✅ **認証フロー全体**をテスト
- ✅ TypeScript/Go 方式と同等

---

### **Level 2: Compliance Tests（準拠テスト）** ← **✅ 実装済み！**

**目的**: プロトコル準拠と他実装との互換性確認

```python
# tests/compliance/test_brc_protocol.py

def test_brc_protocol_compliance():
    """BRCプロトコル準拠テスト"""
    # BRC仕様に準拠した動作を確認
    ...

# tests/compliance/test_express_compatibility.py

def test_express_compatibility():
    """Express middleware互換性テスト"""
    # TypeScript版との互換性を確認
    ...
```

**特徴**:

- 📋 BRC プロトコル準拠確認
- 🔄 Express middleware 互換性
- 📊 標準仕様との整合性

---

### **Level 3: Feature Tests（機能テスト）** ← **✅ 実装済み！**

**目的**: 特定機能の詳細テスト

```python
# tests/features/test_text_plain_support.py
# tests/features/test_multipart_upload.py
```

**特徴**:

- 🎯 機能固有の詳細テスト
- 🔧 エッジケース確認
- 📝 仕様詳細の検証

---

### **Level 4: Network Tests（ネットワークテスト）** ← **✅ 実装済み（オプション）**

**目的**: 実際のネットワークとの互換性をテスト

```python
# tests/testnet/test_auth_flow_testnet.py
# tests/testnet/test_payment_flow_testnet.py

def test_testnet_auth_flow():
    """testnet 認証フロー（実ネットワーク）"""
    # 実際のtestnetネットワークで認証テスト
    ...
```

**特徴**:

- 🌐 実際の testnet ネットワーク使用
- 📊 API 互換性確認
- ⚠️ オプション（リリース前確認用）

---

## 📊 比較表: 現在 vs 推奨

### **現在の testnet テスト（問題あり）**

| テスト         | 分類           | 場所                | 正しい場所              |
| -------------- | -------------- | ------------------- | ----------------------- |
| Wallet 初期化  | py-sdk         | ❌ `tests/testnet/` | ✅ `py-sdk/tests/`      |
| Transport 作成 | 単体           | ❌ `tests/testnet/` | ✅ `tests/unit/`        |
| Peer 初期化    | py-sdk         | ❌ `tests/testnet/` | ✅ `py-sdk/tests/`      |
| Auth endpoint  | **middleware** | ⚠️ `tests/testnet/` | ✅ `tests/integration/` |
| 残高確認       | py-sdk         | ❌ `tests/testnet/` | ✅ `py-sdk/tests/`      |
| WOC API        | py-sdk         | ❌ `tests/testnet/` | ✅ `py-sdk/tests/`      |

### **推奨構成（TypeScript/Go 方式）**

| テスト              | 分類           | 場所                    | 説明                |
| ------------------- | -------------- | ----------------------- | ------------------- |
| **POST JSON**       | **middleware** | ✅ `tests/integration/` | JSON リクエスト処理 |
| **POST Binary**     | **middleware** | ✅ `tests/integration/` | バイナリデータ処理  |
| **GET Request**     | **middleware** | ✅ `tests/integration/` | GET リクエスト処理  |
| **Auth Handshake**  | **middleware** | ✅ `tests/integration/` | 認証ハンドシェイク  |
| **Cert Exchange**   | **middleware** | ✅ `tests/integration/` | 証明書交換          |
| **Unauthenticated** | **middleware** | ✅ `tests/integration/` | 未認証リクエスト    |

---

## 🎯 実施済み修正アクション（2025 年 1 月）

### **✅ 1. 統合テストの作成**

```python
# tests/integration/test_middleware_auth.py

class TestMiddlewareAuthentication:
    """Middleware 認証テスト（TypeScript/Go方式）"""

    def test_01_post_json_authenticated(self):
        """JSON POST（TypeScript Test 1 相当）"""✅ 実装済み

    def test_02_post_url_encoded(self):
        """URL-encoded POST（TypeScript Test 2 相当）"""✅ 実装済み

    def test_03_post_plain_text(self):
        """Plain Text POST（TypeScript Test 3 相当）"""✅ 実装済み

    def test_04_post_binary_data(self):
        """Binary POST（TypeScript Test 4 相当）"""✅ 実装済み

    def test_05_get_request(self):
        """GET Request（TypeScript Test 5 相当）"""✅ 実装済み

    # ... 11テスト実装済み
```

### **✅ 2. 重複テストの削除**

削除されたファイル：

- ❌ test_phase2_3_complete.py（Phase 固有）
- ❌ test_complete_integration.py（重複）
- ❌ test_real_middleware_integration.py（重複）
- ❌ test_transport_complete.py（重複）
- ❌ test_py_sdk_basic.py（py-sdk 固有）
- ❌ test_py_sdk_integration.py（py-sdk 固有）
- ❌ test_peer_initialization.py（py-sdk 固有）
- ❌ test_wallet_interface.py（py-sdk 固有）

**合計 8 ファイル削除**

### **✅ 3. テストの再編成**

移動されたファイル：

- test_brc_protocol_compliance.py → compliance/test_brc_protocol.py
- test_express_compatibility.py → compliance/test_express_compatibility.py
- test_text_plain_support.py → features/test_text_plain_support.py
- test_bsv_multipart_upload.py → features/test_multipart_upload.py

**合計 4 ファイル移動**

---

## 📝 まとめ（2025 年 1 月更新）

### **✅ 解決済み問題**

✅ ~~現在の testnet テストは **py-sdk のテスト** になっている~~  
✅ ~~**ミドルウェアのテスト** が不足している~~  
✅ ~~TypeScript/Go 版の正しいアプローチと異なる~~

### **✅ 実装済み解決策**

✅ py-sdk テストは削除（py-sdk リポジトリで管理すべき）  
✅ Middleware テストは `tests/integration/` に実装済み  
✅ TypeScript/Go 方式の統合テストを実装済み  
✅ testnet テストは整理・最小化済み

### **📊 最終状態**

| カテゴリ             | ファイル数 | 状態                |
| -------------------- | ---------- | ------------------- |
| **Core Integration** | 1          | ✅ 完了 (11 テスト) |
| **Compliance**       | 2          | ✅ 整理済み         |
| **Features**         | 2          | ✅ 整理済み         |
| **Testnet**          | 9          | ✅ 整理済み         |
| **Individual Tests** | 8          | ✅ 保持             |
| **削除**             | 8          | ✅ 完了             |

**総合**: 29 ファイル → 21 ファイル（8 ファイル削減、4 ファイル再編成）

### **🎯 結論**

✅ **Python 版のテストは TypeScript/Go 版と同等またはそれ以上**  
✅ **テスト構造が明確で保守しやすい**  
✅ **重複が削減され、効率的**

最終更新：2025 年 1 月
