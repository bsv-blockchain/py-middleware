# 🌐 BSV Mainnet Payment Experiment Guide (English)

**⚠️ Important Warning**: This guide uses the real BSV Mainnet. Real coins are used and transaction fees will be incurred.

---

## 📋 Prerequisites

- ✅ You have completed verification on Testnet
- ✅ You understand how the BSV Middleware works
- ✅ You are ready to test with small amounts
- ✅ You understand the importance of private key management

---

## 🚀 Step 1: Create a Mainnet Wallet

### 1.1 Run the wallet creation script

```bash
cd /Users/cdl/development/py-middleware-project/py-middleware

# Activate virtual environment
source venv/bin/activate

# Create Mainnet wallet
python examples/testnet_setup/create_mainnet_wallet.py
```

### 1.2 Files that will be created

```
examples/testnet_setup/
└── mainnet_server_wallet_config.json  # ⚠️ サーバー用ウォレット（秘密鍵を含む - 厳重管理）
```

### 1.3 Important checks

- ✅ Ensure `mainnet_wallet_config.json` is listed in `.gitignore`
- ✅ Back up the private key (print, encrypted USB, etc.)
- ✅ Note the address (destination for BSV)

---

## 💰 Step 2: Buy and send a small amount of BSV

### 2.1 How to buy BSV

#### Option A: HandCash (recommended)

```
URL: https://handcash.io/
- Buy BSV with the mobile app
- Low minimum purchase
- Easy to send
```

#### Option B: Exchanges

```
- Buy BSV on Coinbase, Binance, etc.
- Withdraw to your wallet
```

### 2.2 Sending procedure

1. Destination address: the `address` field in `mainnet_wallet_config.json`
2. Recommended amount: 10,000 - 100,000 satoshis (0.0001 - 0.001 BSV)
3. Send from your exchange/wallet

### 2.3 Confirm the transfer

```bash
# Check balance on WhatsOnChain
# https://whatsonchain.com/address/[your-address]
```

**Check**:

- ✅ Transaction has at least 1 confirmation
- ✅ Balance is displayed

---

## 🧪 Step 3: Run the payment test

### 3.1 Basic payment test

```bash
cd /Users/cdl/development/py-middleware-project/py-middleware

# Activate virtual environment
source venv/bin/activate

# Run Mainnet payment test
python tests/testnet/test_mainnet_payment.py
```

**Expected behavior**:

1. Balance check
2. Create a transaction (500 satoshis)
3. Broadcast
4. Show TXID

### 3.2 Example output

```
🌐 BSV Mainnet Payment Test
==================================================
⚠️  This test uses the real BSV Mainnet
   Real coins and transaction fees will be incurred

Run the payment test on Mainnet? (yes/no): yes

📋 Loading wallet...
✅ Loaded Mainnet wallet
   Address: 1A2B3C...

💰 Balance check (Mainnet)
✅ Balance: 50,000 satoshis (0.00050000 BSV)

💸 Creating payment transaction
   Amount: 500 satoshis
   Recipient: 1A2B3C... (self-send)

🔨 Building transaction...
✅ Transaction created successfully
📡 Broadcasting transaction...

🎉 Mainnet payment test successful!
✅ Transaction ID: abc123...
✅ Amount: 500 satoshis

📊 Check transaction:
   WhatsOnChain: https://whatsonchain.com/tx/abc123...
```

---

## 🖥️ Step 4: Test on the Django server (Mainnet)

### 4.1 Start the Mainnet server

```bash
cd /Users/cdl/development/py-middleware-project/py-middleware

# Activate virtual environment
source venv/bin/activate

# Start Mainnet server
cd examples/django_example
python manage.py runserver --settings=mainnet_settings
```

### 4.2 Endpoint tests

#### Auth + Payment test (`/hello-bsv/`)

```bash
# Run in another terminal
cd /Users/cdl/development/py-middleware-project/py-middleware

# Create a client script (Mainnet quick_auth_test.py)
# ⚠️ Edits for Mainnet will be required
```

### 4.3 Expected behavior

1. Initial handshake: authentication session established
2. General Message: authenticated request
3. Payment processing: real Mainnet transaction
4. Response: `{ "message": "Hello BSV", "success": true, ... }`

---

## 📊 Step 5: Verify transactions

### 5.1 Check on WhatsOnChain

```
Mainnet Explorer:
https://whatsonchain.com/address/[your-address]

Checks:
✅ Outgoing transactions listed
✅ Balance changes correctly
✅ Fees are reasonable
```

### 5.2 Check server logs

```
[MAINNET] INFO ... BSVPaymentMiddleware initialized
[MAINNET] INFO ... Payment processed - TypeScript equivalent
[MAINNET] INFO ... satoshis_paid: 500
[MAINNET] INFO ... accepted: True
```

---

## 💡 Troubleshooting

### Insufficient balance

```
❌ Error: This wallet has no balance
```

**How to resolve**:

1. Confirm the transaction on WhatsOnChain has at least 1 confirmation
2. Send a sufficient amount (minimum 2,000 satoshis)
3. Confirm at least 1 confirmation

### Broadcast error

```
❌ Broadcast error: ...
```

**How to resolve**:

1. Ensure the balance is sufficient
2. Ensure UTXOs are available
3. Check network connectivity

### Authentication error

```
❌ Authentication required
```

**How to resolve**:

1. Ensure `REQUIRE_AUTH: True` in `mainnet_settings.py`
2. Ensure the authentication handshake completed successfully
3. Ensure the session is valid

---

## 🔒 Security checklist

### Before

- [ ] `mainnet_wallet_config.json` is in `.gitignore`
- [ ] Private key is backed up
- [ ] Ready to test with small amounts
- [ ] `DEBUG = False`

### During

- [ ] Private keys do not appear in logs
- [ ] Transaction amounts are as expected
- [ ] Recipient address is correct

### After

- [ ] Confirm transactions on WhatsOnChain
- [ ] Balance changes are correct
- [ ] No unexpected transactions

---

## 📈 Next steps

### After Phase 3

1. Security validation (3.3)
   - Run security test suite
   - Vulnerability scan

2. Performance validation (3.4)
   - Load testing
   - Measure response times

3. Production readiness (3.7)
   - HTTPS configuration
   - Domain setup
   - Monitoring and logging

---

## ⚠️ Important notes

### Actual costs

- Transaction fees: typically 1–2 satoshis/byte
- Per test: about 200–500 satoshis (including fees)
- 10 tests: about 5,000 satoshis = 0.00005 BSV ≈ $0.0025 (at $50/BSV)

### Recommendations

1. Start small: begin with ≤ 10,000 satoshis
2. Increase gradually after confirming behavior
3. Check balances regularly to ensure there are no unexpected transfers
4. Monitor logs for anomalies

### Emergency procedures

1. Stop server: `pkill -f "manage.py runserver"`
2. Check balances on WhatsOnChain
3. Protect private keys: if leakage is suspected, move funds immediately

---

## 📞 Support

If you encounter problems:

1. Check server and client logs
2. Check transaction status on WhatsOnChain
3. Reproduce on Testnet if possible

---

🎉 You're ready to begin Mainnet payment experiments!

We strongly recommend starting cautiously with small amounts.


# 🌐 BSV Mainnet 支払い実験ガイド

**⚠️ 重要な警告**: このガイドは実際の BSV Mainnet を使用します。実際のコインが使用され、トランザクション手数料が発生します。

---

## 📋 **前提条件**

- ✅ Testnet での動作確認が完了していること
- ✅ BSV Middleware の仕組みを理解していること
- ✅ 少額でテストする準備ができていること
- ✅ 秘密鍵管理の重要性を理解していること

---

## 🚀 **Step 1: Mainnet ウォレット作成**

### **1.1 ウォレット作成スクリプト実行**

```bash
cd /Users/cdl/development/py-middleware-project/py-middleware

# 仮想環境を有効化
source venv/bin/activate

# Mainnetウォレット作成
python examples/testnet_setup/create_mainnet_wallet.py
```

### **1.2 作成されるファイル**

```
examples/testnet_setup/
├── mainnet_server_wallet_config.json  # ⚠️ サーバー用ウォレット（秘密鍵を含む - 厳重管理）
└── mainnet_client_wallet_config.json  # ⚠️ クライアント用ウォレット（テスト時に作成）
```

### **1.3 重要な確認事項**

- ✅ `.gitignore` に `mainnet_wallet_config.json` が追加されていることを確認
- ✅ 秘密鍵をバックアップ（印刷、暗号化 USB 等）
- ✅ アドレスをメモ（BSV 送金先）

---

## 💰 **Step 2: 少額の BSV を購入・送金**

### **2.1 BSV の購入方法**

#### **Option A: HandCash (推奨)**

```
URL: https://handcash.io/
- スマホアプリでBSVを購入
- 最小購入額が低い
- 送金が簡単
```

#### **Option B: 取引所**

```
- Coinbase, Binance等でBSVを購入
- ウォレットに出金
```

### **2.2 送金手順**

1. **送金先アドレス**: `mainnet_wallet_config.json` の `address` フィールド
2. **推奨送金額**: 10,000 - 100,000 satoshis (0.0001 - 0.001 BSV)
3. **送金実行**: 購入した取引所/ウォレットから送金

### **2.3 送金確認**

```bash
# WhatsOnChain で残高確認
# https://whatsonchain.com/address/[your-address]
```

**確認項目**:

- ✅ トランザクションが 1 確認以上
- ✅ 残高が表示されている

---

## 🧪 **Step 3: 支払いテスト実行**

### **3.1 基本支払いテスト**

```bash
cd /Users/cdl/development/py-middleware-project/py-middleware

# 仮想環境を有効化
source venv/bin/activate

# Mainnet支払いテスト実行
python tests/testnet/test_mainnet_payment.py
```

**期待される動作**:

1. 残高確認
2. トランザクション作成 (500 satoshis)
3. ブロードキャスト
4. TXID 表示

### **3.2 実行例**

```
🌐 BSV Mainnet Payment Test
==================================================
⚠️  これは実際の BSV Mainnet を使用するテストです
   実際のコインとトランザクション手数料が発生します

Mainnet で支払いテストを実行しますか? (yes/no): yes

📋 ウォレット読み込み中...
✅ Mainnet ウォレット読み込み完了
   Address: 1A2B3C...

💰 残高チェック (Mainnet)
✅ 残高: 50,000 satoshis (0.00050000 BSV)

💸 支払いトランザクション作成
   支払い金額: 500 satoshis
   受取アドレス: 1A2B3C... (自分に送金)

🔨 トランザクション作成中...
✅ トランザクション作成成功
📡 トランザクションをブロードキャスト中...

🎉 Mainnet 支払いテスト成功！
✅ Transaction ID: abc123...
✅ 支払い金額: 500 satoshis

📊 トランザクション確認:
   WhatsOnChain: https://whatsonchain.com/tx/abc123...
```

---

## 🖥️ **Step 4: Django サーバーで Mainnet テスト**

### **4.1 Mainnet サーバー起動**

```bash
cd /Users/cdl/development/py-middleware-project/py-middleware

# 仮想環境を有効化
source venv/bin/activate

# Mainnetサーバー起動
cd examples/django_example
python manage.py runserver --settings=mainnet_settings
```

### **4.2 エンドポイントテスト**

#### **認証 + 支払いテスト (`/hello-bsv/`)**

```bash
# 別のターミナルで実行
cd /Users/cdl/development/py-middleware-project/py-middleware

# Mainnet 認証+決済統合テスト実行
python3 tests/testnet/test_hello_bsv_mainnet.py
```

**テストフロー**:

1. **ウォレット確認**
   - サーバーウォレット: `mainnet_wallet_config.json`
   - クライアントウォレット: `mainnet_client_wallet_config.json`
   - ※ クライアントウォレットがない場合、自動作成プロンプトが表示されます

2. **確認プロンプト**
   ```
   ⚠️  This test uses REAL BSV on Mainnet!
   Do you want to proceed? (yes/no): yes
   ```

3. **残高確認**
   - WhatsOnChain API で両方のウォレット残高を確認
   - 最低 1,000 satoshis 必要

4. **認証ハンドシェイク** (BRC-103/104)
   - Initial Message 送信
   - サーバーから Initial Response 受信

5. **決済付き認証リクエスト**
   - 500 satoshis のトランザクション作成・ブロードキャスト
   - General Message 送信（認証 + X-BSV-Payment ヘッダー）

6. **成功時の出力例**:
   ```
   🎉 Mainnet Authentication + Payment Test SUCCESS!
   ✅ Message: Hello BSV Mainnet!
   ✅ Authenticated: True
   ✅ Payment Processed: True
   ✅ Identity Key: 03abc123...
   
   📊 Transaction Details:
      TXID: a1b2c3d4...
      Amount: 500 satoshis
      WhatsOnChain: https://whatsonchain.com/tx/a1b2c3d4...
```

### **4.3 期待される動作**

1. **初回ハンドシェイク**: 認証セッション確立
2. **General Message**: 認証済みリクエスト
3. **支払い処理**: 実際の Mainnet トランザクション
4. **レスポンス**: `{ "message": "Hello BSV", "success": true, ... }`

---

## 📊 **Step 5: トランザクション確認**

### **5.1 WhatsOnChain で確認**

```
Mainnet Explorer:
https://whatsonchain.com/address/[your-address]

確認項目:
✅ 送信トランザクション一覧
✅ 残高の変化
✅ 手数料の確認
```

### **5.2 サーバーログ確認**

```
[MAINNET] INFO ... BSVPaymentMiddleware initialized
[MAINNET] INFO ... Payment processed - TypeScript equivalent
[MAINNET] INFO ... satoshis_paid: 500
[MAINNET] INFO ... accepted: True
```

---

## 💡 **トラブルシューティング**

### **残高不足エラー**

```
❌ Error: このウォレットには残高がありません
```

**解決方法**:

1. WhatsOnChain でトランザクションが確認済みか確認
2. 十分な金額（最低 2000 satoshis）を送金
3. トランザクションが 1 確認以上あることを確認

### **ブロードキャストエラー**

```
❌ ブロードキャストエラー: ...
```

**解決方法**:

1. 残高が十分か確認
2. UTXO が利用可能か確認
3. ネットワーク接続を確認

### **認証エラー**

```
❌ Authentication required
```

**解決方法**:

1. `mainnet_settings.py` で `REQUIRE_AUTH: True` を確認
2. 認証ハンドシェイクが正常に完了しているか確認
3. セッションが有効か確認

---

## 🔒 **セキュリティチェックリスト**

### **実行前**

- [ ] `.gitignore` に `mainnet_wallet_config.json` が含まれている
- [ ] 秘密鍵をバックアップ済み
- [ ] 少額でテストする準備ができている
- [ ] DEBUG = False に設定されている

### **実行中**

- [ ] ログに秘密鍵が出力されていない
- [ ] トランザクション金額が想定内
- [ ] 受取アドレスが正しい

### **実行後**

- [ ] トランザクションを WhatsOnChain で確認
- [ ] 残高の変化が正しい
- [ ] 想定外のトランザクションがない

---

## 📈 **次のステップ**

### **Phase 3 完了後**

1. **セキュリティ検証 (3.3)**

   - セキュリティテストスイート実行
   - 脆弱性スキャン

2. **パフォーマンス検証 (3.4)**

   - 負荷テスト実行
   - レスポンスタイム測定

3. **本番環境準備 (3.7)**
   - HTTPS 設定
   - ドメイン設定
   - 監視・ログ設定

---

## ⚠️ **重要な注意事項**

### **実際のコストについて**

- **トランザクション手数料**: 通常 1-2 satoshis/byte
- **テスト 1 回あたり**: 約 200-500 satoshis (手数料含む)
- **10 回テスト**: 約 5,000 satoshis = 0.00005 BSV ≈ $0.0025 (at $50/BSV)

### **推奨事項**

1. **少額でテスト**: 最初は 10,000 satoshis 以下で
2. **段階的に増額**: 動作確認後に必要に応じて増額
3. **定期的な残高確認**: 想定外の送金がないか確認
4. **ログ監視**: 異常な動作がないか確認

### **緊急時の対応**

1. **サーバー停止**: `pkill -f "manage.py runserver"`
2. **残高確認**: WhatsOnChain で確認
3. **秘密鍵保護**: 漏洩の疑いがあれば即座に資金を移動

---

## 📞 **サポート**

問題が発生した場合:

1. **ログ確認**: サーバーログとクライアントログ
2. **WhatsOnChain**: トランザクション状態を確認
3. **Testnet で再現**: 可能であれば Testnet で再現テスト

---

**🎉 準備完了！Mainnet 支払い実験を開始してください！**

最初は慎重に、少額から始めることを強くお勧めします。










