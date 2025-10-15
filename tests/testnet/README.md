# 🧪 BSV Testnet Integration Tests

Testnet 環境での統合テストスイート

## 📋 概要

このディレクトリには、実際の BSV testnet ネットワークを使用した統合テストが含まれています。

**重要**: これらのテストは実際の testnet ネットワークに接続します。事前に testnet ウォレットとコインを準備してください。

## 🚀 クイックスタート

### 前提条件

1. **Testnet ウォレット作成**:

   ```bash
   cd examples/testnet_setup
   python create_testnet_wallet.py
   ```

2. **Testnet コイン取得**:

   - Faucet: https://faucet.bitcoincloud.net/
   - ウォレット作成時に表示されたアドレスを使用

3. **接続テスト**:
   ```bash
   python examples/testnet_setup/test_testnet_connection.py
   ```

### テスト実行

**全ての testnet テストを実行**:

```bash
python -m pytest tests/testnet/ -v
```

**特定のテストを実行**:

```bash
# 認証フローテスト
python tests/testnet/test_auth_flow_testnet.py

# 支払いフローテスト
python tests/testnet/test_payment_flow_testnet.py
```

## 📁 テストファイル

### `test_auth_flow_testnet.py`

Testnet 環境での認証フロー統合テスト

**テスト内容**:

- ✅ Testnet ウォレット初期化
- ✅ DjangoTransport 作成
- ✅ Peer 初期化
- ✅ `/.well-known/bsv/auth` エンドポイント
- ✅ Testnet 残高確認
- ✅ WhatsOnChain API 接続

**実行**:

```bash
python tests/testnet/test_auth_flow_testnet.py
```

### `test_payment_flow_testnet.py`

Testnet 環境での支払いフロー統合テスト

**テスト内容**:

- ✅ Testnet 残高確認
- ✅ PaymentMiddleware 初期化
- ✅ 402 Payment Required レスポンス
- ✅ Transaction 作成
- ✅ ARC Broadcaster 接続確認
- ✅ WhatsOnChain トランザクション確認

**実行**:

```bash
python tests/testnet/test_payment_flow_testnet.py
```

## 🔧 トラブルシューティング

### 問題 1: "Testnet wallet not found"

```bash
Error: Testnet wallet not found: testnet_wallet_config.json
```

**解決方法**:

```bash
cd examples/testnet_setup
python create_testnet_wallet.py
```

### 問題 2: "No testnet balance"

```bash
Warning: 残高が 0 です
```

**解決方法**:

1. Faucet からコインを取得:
   - https://faucet.bitcoincloud.net/
   - ウォレットアドレスを入力
2. 数分待ってから再実行

### 問題 3: "WhatsOnChain API connection failed"

```bash
Error: WhatsOnChain API 接続失敗
```

**解決方法**:

1. インターネット接続を確認
2. API エンドポイントを確認:
   ```
   https://api.whatsonchain.com/v1/bsv/test
   ```
3. レート制限を確認 (しばらく待つ)

### 問題 4: "ARC Broadcaster エラー"

```bash
Error: ARC Broadcaster レスポンス: 500
```

**解決方法**:

1. Testnet ARC エンドポイントを確認:
   ```
   https://api.taal.com/arc/testnet
   ```
2. 別の ARC エンドポイントを試す
3. しばらく待ってから再試行

## 📊 テスト戦略

### Testnet テストの目的

1. **実環境動作確認**: 実際のブロックチェーンネットワークでの動作確認
2. **統合テスト**: py-sdk、middleware、Django の統合動作確認
3. **エラーケース検証**: ネットワークエラー、残高不足などの実際のエラー
4. **パフォーマンス確認**: 実際のネットワーク遅延を含めた性能確認

### Testnet vs Unit Tests

| 項目     | Unit Tests   | Testnet Tests  |
| -------- | ------------ | -------------- |
| 実行速度 | 速い (秒)    | 遅い (分)      |
| 外部依存 | なし         | あり (testnet) |
| コスト   | 無料         | 無料           |
| 目的     | ロジック検証 | 統合動作確認   |

### テスト実行タイミング

**Unit Tests**:

- コード変更のたびに実行
- CI/CD で自動実行

**Testnet Tests**:

- 主要機能追加時
- リリース前
- mainnet デプロイ前

## 🌟 ベストプラクティス

### 1. Testnet コインの管理

```bash
# 残高確認
curl https://api.whatsonchain.com/v1/bsv/test/address/{your_address}/balance

# トランザクション履歴
curl https://api.whatsonchain.com/v1/bsv/test/address/{your_address}/history
```

### 2. ログの活用

```python
# テスト実行時に詳細ログを表示
python -m pytest tests/testnet/ -v -s

# ログレベルを DEBUG に設定
export LOG_LEVEL=DEBUG
```

### 3. エラーハンドリング

Testnet テストはネットワーク状況により失敗することがあります：

```python
# Testnet 特有のエラーを適切にスキップ
@pytest.mark.skipif(not has_testnet_balance(), reason="No testnet balance")
def test_with_balance():
    pass
```

### 4. CI/CD 統合

```yaml
# GitHub Actions example
- name: Run Testnet Tests
  run: |
    python examples/testnet_setup/create_testnet_wallet.py
    # Get testnet coins from faucet (manual step)
    python -m pytest tests/testnet/ -v
  env:
    BSV_NETWORK: testnet
```

## 📚 次のステップ

### 1. テストカバレッジ拡大

```bash
# 追加テストファイル作成
tests/testnet/test_integration_testnet.py  # 統合テスト
tests/testnet/test_error_handling_testnet.py  # エラー処理
tests/testnet/test_performance_testnet.py  # パフォーマンス
```

### 2. Mainnet 移行準備

Testnet で全てのテストが成功したら：

1. **セキュリティレビュー**: コードとテスト結果を再確認
2. **小額テスト**: Mainnet で小額から開始
3. **段階的スケールアップ**: 徐々に利用を拡大

### 3. 監視とアラート

```bash
# Testnet での継続的監視
- トランザクション成功率
- API レスポンス時間
- エラー発生頻度
```

## 🔗 関連ドキュメント

- **Testnet Setup Guide**: `examples/testnet_setup/README.md`
- **API Reference**: `docs/api_reference.md`
- **Troubleshooting**: `docs/troubleshooting.md`
- **Mainnet Deployment**: `docs/mainnet_deployment_guide.md`

## 📞 サポート

問題が解決しない場合：

1. **ドキュメント確認**: 関連ドキュメントを参照
2. **Issue 作成**: GitHub で issue を報告
3. **コミュニティ**: BSV Slack/Discord でサポート

---

**Happy Testing on Testnet!** 🎉

Testnet は完全に無料で安全です。思う存分テストして、完璧な状態で mainnet へ移行しましょう！
