# BSV Python Middleware (Hybrid Architecture)

BSV BRC-100 対応の Python ミドルウェアライブラリ - **ハイブリッドアプローチ** で Django、FastAPI 向けの相互認証と支払い機能を提供

## 概要

このライブラリは、BSV（Bitcoin SV）ブロックチェーンの BRC-103/BRC-104 仕様に基づく相互認証と支払い機能を Python の Web フレームワークに統合するためのミドルウェアです。**[py-sdk の `feature/auth/certificates-port` ブランチ](https://github.com/bsv-blockchain/py-sdk/tree/feature/auth/certificates-port)** を活用し、**ハイブリッドアーキテクチャ (WSGI Core + Framework Adapters)** を採用しています。

## アーキテクチャ

### ハイブリッドアプローチ: WSGI Core + Framework Adapters

```
Web Framework → Framework Adapter → WSGI Core → py-sdk Integration → BSV Network
```

この設計により：

- **フレームワーク非依存**: WSGI Core は任意のフレームワークで動作
- **統一された機能**: すべてのフレームワークで同一の BSV 機能
- **拡張性**: 新しいフレームワークはアダプター追加のみで対応可能
- **py-sdk 活用**: BSV 認証・支払い機能を py-sdk から直接利用

## 主な機能

- **相互認証**: BRC-103 仕様に基づくピア間の暗号学的認証（py-sdk 提供）
- **支払い統合**: BSV マイクロペイメントによる API 収益化（py-sdk 提供）
- **証明書管理**: 検証可能な証明書の交換と選択的開示（py-sdk 提供）
- **multipart/form-data 対応**: BSV 認証付きファイルアップロード機能
- **ハイブリッドアーキテクチャ**: WSGI Core + Framework Adapters
- **セキュア**: エンドツーエンドの暗号化とセキュリティ

## 対応仕様

- [BRC-103: Peer-to-Peer Mutual Authentication and Certificate Exchange Protocol](https://github.com/bitcoin-sv/BRCs/blob/master/peer-to-peer/0103.md)
- [BRC-104: HTTP Transport for BRC-103 Mutual Authentication](https://github.com/bitcoin-sv/BRCs/blob/master/peer-to-peer/0104.md)

## 対応フレームワーク

- **Django** - 大規模アプリケーション向け（Phase 1 実装中）
- **FastAPI** - 非同期処理と API ドキュメント自動生成対応（Phase 2 予定）

> **実装戦略**: ハイブリッドアプローチにより、WSGI Core + Django Adapter から開始し、FastAPI Adapter を追加する段階的アプローチを採用

## インストール

```bash
# py-sdk development branch が必要
pip install git+https://github.com/bsv-blockchain/py-sdk.git@feature/auth/certificates-port

# bsv-middleware (開発中)
pip install -e .

# フレームワーク固有の依存関係
pip install django>=3.2.0  # Django を使用する場合
pip install fastapi>=0.70.0 uvicorn>=0.15.0  # FastAPI を使用する場合
```

## クイックスタート

### Django (ハイブリッドアプローチ)

```python
# settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'bsv_middleware.integrations.django.middleware.BSVAuthMiddleware',
    'bsv_middleware.integrations.django.middleware.BSVPaymentMiddleware',
    # ... other middleware
]

BSV_MIDDLEWARE = {
    # py-sdk wallet instance
    'WALLET': my_py_sdk_wallet,
    'ALLOW_UNAUTHENTICATED': False,
    'CALCULATE_REQUEST_PRICE': lambda request: 100,  # 100サトシ
    # py-sdk specific configurations
    'CERTIFICATE_REQUESTS': {
        'certifiers': ['<33-byte-pubkey-of-certifier>'],
        'types': {
            'age-verification': ['dateOfBirth', 'country']
        }
    },
    'ON_CERTIFICATES_RECEIVED': handle_certificates
}

# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def protected_endpoint(request):
    # ハイブリッドアプローチ: WSGI Core からの認証情報
    if hasattr(request, 'bsv_auth') and request.bsv_auth.identity_key != 'unknown':
        return JsonResponse({
            "message": f"Hello, {request.bsv_auth.identity_key}",
            "certificates": request.bsv_auth.certificates
        })
    return JsonResponse({"error": "Unauthorized"}, status=401)

@require_http_methods(["GET"])
def paid_content(request):
    # 支払いが完了している場合のみアクセス可能
    return JsonResponse({
        "content": "This is premium content",
        "paid": request.bsv_payment.satoshis_paid,
        "transaction_id": request.bsv_payment.transaction_id
    })

def handle_certificates(sender_public_key, certificates, request, response, next_func):
    # py-sdk certificate handling
    print(f"Received {len(certificates)} certificates from {sender_public_key}")
    for cert in certificates:
        # py-sdk VerifiableCertificate integration
        if cert.type == 'age-verification':
            age = cert.fields.get('age')
            if age and int(age) >= 18:
                print(f"Age verified: {age}")
    next_func()
```

### FastAPI (ハイブリッドアプローチ - Phase 2)

```python
from fastapi import FastAPI, Depends, Request
from bsv_middleware.integrations.fastapi.middleware import BSVAuthMiddleware, BSVPaymentMiddleware
from bsv_middleware.integrations.fastapi.dependencies import get_bsv_auth, get_bsv_payment

app = FastAPI()

# ハイブリッドアプローチ: WSGI Core経由でミドルウェア追加
app.add_middleware(
    BSVAuthMiddleware,
    wallet=my_py_sdk_wallet,
    certificate_requests={
        'certifiers': ['<33-byte-pubkey>'],
        'types': {'age-verification': ['age']}
    }
)
app.add_middleware(BSVPaymentMiddleware, wallet=my_py_sdk_wallet)

@app.get("/protected")
async def protected_endpoint(bsv_auth: dict = Depends(get_bsv_auth)):
    return {
        "message": f"Hello, {bsv_auth['identity_key']}",
        "certificates": bsv_auth.get('certificates', [])
    }

@app.get("/premium")
async def premium_content(
    bsv_auth: dict = Depends(get_bsv_auth),
    bsv_payment: dict = Depends(get_bsv_payment)
):
    return {
        "content": "Premium content",
        "user": bsv_auth['identity_key'],
        "paid": bsv_payment['satoshis_paid'],
        "transaction_id": bsv_payment['transaction_id']
    }
```

## プロジェクト状況

🚧 **開発中** - このプロジェクトは現在開発段階にあります。

### 実装ロードマップ

- [x] プロジェクト計画の策定
- [x] 実装難易度分析・戦略決定
- [x] ハイブリッドアプローチの採用決定
- [x] py-sdk feature/auth/certificates-port 依存関係の確立
- [ ] Phase 1: WSGI Core + Django Adapter 実装（4-5 週間）
- [ ] Phase 2: Django 最適化・公開準備（1 週間）
- [ ] Phase 3: FastAPI Adapter Implementation（Django 版成功後）
- [ ] Phase 4: Advanced Features & Long-term Support

詳細なプランについては [PROJECT_PLAN.md](./PROJECT_PLAN.md) をご覧ください。

## 参考実装

このプロジェクトは以下の既存実装を参考にしています：

- [@bsv/auth-express-middleware](https://github.com/bitcoin-sv/auth-express-middleware) - TypeScript Express 認証ミドルウェア
- [@bsv/payment-express-middleware](https://github.com/bitcoin-sv/payment-express-middleware) - TypeScript Express 支払いミドルウェア
- [go-bsv-middleware](https://github.com/bitcoin-sv/go-bsv-middleware) - Go 言語実装

## 貢献

プロジェクトへの貢献を歓迎します！

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ライセンス

Open BSV License - 詳細は [LICENSE](LICENSE) ファイルをご覧ください。

## サポート

質問やバグ報告、機能リクエストについては、GitHub の Issue を作成してください。

---

**注意**: このライブラリは現在開発中です。プロダクション環境での使用前に十分なテストを行ってください。
