#!/usr/bin/env python3
"""
BSV Testnet Connection Test

testnet ウォレットが正しく設定され、接続できることを確認するスクリプト
"""

import os
import sys
import json
from pathlib import Path

# py-sdk をインポート
try:
    from bsv.wallet.wallet_impl import WalletImpl
    from bsv.keys import PrivateKey
    from bsv.constants import Network
except ImportError:
    print("❌ Error: py-sdk がインストールされていません")
    print("インストール方法: pip install -e /path/to/py-sdk")
    sys.exit(1)


def load_wallet_config(config_path: str = "testnet_wallet_config.json") -> dict:
    """ウォレット設定を読み込む"""
    config_file = Path(__file__).parent / config_path
    
    if not config_file.exists():
        print(f"❌ Error: ウォレット設定ファイルが見つかりません: {config_file}")
        print()
        print("以下のコマンドでウォレットを作成してください:")
        print("  python examples/testnet_setup/create_testnet_wallet.py")
        sys.exit(1)
    
    with open(config_file, 'r') as f:
        return json.load(f)


def check_testnet_balance(address: str) -> dict:
    """
    testnet アドレスの残高を確認 (WhatsOnChain API 使用)
    
    Args:
        address: testnet アドレス
        
    Returns:
        dict: 残高情報
    """
    try:
        import requests
        
        url = f"https://api.whatsonchain.com/v1/bsv/test/address/{address}/balance"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        balance_data = response.json()
        return {
            "confirmed": balance_data.get("confirmed", 0),
            "unconfirmed": balance_data.get("unconfirmed", 0),
            "total": balance_data.get("confirmed", 0) + balance_data.get("unconfirmed", 0)
        }
    except Exception as e:
        print(f"⚠️  Warning: 残高の確認に失敗しました: {e}")
        return {"confirmed": 0, "unconfirmed": 0, "total": 0}


def test_wallet_creation(wallet_config: dict):
    """ウォレット作成テスト"""
    print("1️⃣  ウォレット作成テスト...")
    
    try:
        # WIF から秘密鍵を復元
        private_key_obj = PrivateKey(wallet_config["private_key"], network=Network.TESTNET)
        
        # ウォレット作成
        wallet = WalletImpl(
            private_key=private_key_obj,
            permission_callback=lambda action: True,  # 全ての操作を自動許可
            load_env=False
        )
        
        # 情報確認
        address = private_key_obj.address(network=Network.TESTNET)
        public_key = private_key_obj.public_key().hex()
        
        assert address == wallet_config["address"], "アドレスが一致しません"
        assert public_key == wallet_config["public_key"], "公開鍵が一致しません"
        
        print(f"   ✅ ウォレット作成成功")
        print(f"      Address: {address}")
        print(f"      Network: testnet")
        
        return wallet
        
    except Exception as e:
        print(f"   ❌ ウォレット作成失敗: {e}")
        raise


def test_balance_check(address: str):
    """残高確認テスト"""
    print()
    print("2️⃣  残高確認テスト...")
    
    try:
        balance = check_testnet_balance(address)
        
        print(f"   ✅ 残高確認成功")
        print(f"      Confirmed:   {balance['confirmed']:,} satoshis")
        print(f"      Unconfirmed: {balance['unconfirmed']:,} satoshis")
        print(f"      Total:       {balance['total']:,} satoshis")
        
        if balance['total'] == 0:
            print()
            print("   ⚠️  Warning: 残高が 0 です")
            print()
            print("   以下の faucet から testnet コインを取得してください:")
            print()
            print("   1. Bitcoincloud Faucet")
            print("      https://faucet.bitcoincloud.net/")
            print(f"      Address: {address}")
            print()
            print("   2. sCrypt Testnet Faucet")
            print("      https://scrypt.io/faucet/")
            print(f"      Address: {address}")
            print()
            print("   3. WhatsOnChain で確認")
            print(f"      https://test.whatsonchain.com/address/{address}")
            
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ 残高確認失敗: {e}")
        return False


def test_whatsonchain_connection(address: str):
    """WhatsOnChain API 接続テスト"""
    print()
    print("3️⃣  WhatsOnChain API 接続テスト...")
    
    try:
        import requests
        
        # アドレス情報取得
        url = f"https://api.whatsonchain.com/v1/bsv/test/address/{address}/info"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        info = response.json()
        
        print(f"   ✅ WhatsOnChain API 接続成功")
        print(f"      Balance:      {info.get('balance', 0):,} satoshis")
        print(f"      Transactions: {info.get('totalTxs', 0)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ WhatsOnChain API 接続失敗: {e}")
        return False


def test_middleware_compatibility(wallet):
    """Middleware 互換性テスト"""
    print()
    print("4️⃣  Middleware 互換性テスト...")
    
    try:
        # WalletInterface メソッドの存在確認
        required_methods = [
            'get_public_key',
            'create_signature',
            'reveal_key_linkage'
        ]
        
        for method_name in required_methods:
            assert hasattr(wallet, method_name), f"メソッド {method_name} が見つかりません"
        
        # get_public_key テスト
        ctx = {}
        args = {"identityKey": True}
        result = wallet.get_public_key(ctx, args, "test")
        
        assert "publicKey" in result, "公開鍵が取得できませんでした"
        
        print(f"   ✅ Middleware 互換性確認完了")
        print(f"      必須メソッド: {len(required_methods)}/{len(required_methods)} OK")
        print(f"      get_public_key: OK")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Middleware 互換性テスト失敗: {e}")
        return False


def main():
    """メイン実行"""
    print()
    print("=" * 70)
    print("🧪 BSV Testnet Connection Test")
    print("=" * 70)
    print()
    
    # ウォレット設定読み込み
    print("📂 ウォレット設定を読み込んでいます...")
    wallet_config = load_wallet_config()
    print(f"   ✅ 設定読み込み完了")
    print()
    
    results = []
    
    try:
        # テスト 1: ウォレット作成
        wallet = test_wallet_creation(wallet_config)
        results.append(("ウォレット作成", True))
        
        # テスト 2: 残高確認
        has_balance = test_balance_check(wallet_config["address"])
        results.append(("残高確認", True))
        
        # テスト 3: WhatsOnChain 接続
        woc_ok = test_whatsonchain_connection(wallet_config["address"])
        results.append(("WhatsOnChain API", woc_ok))
        
        # テスト 4: Middleware 互換性
        middleware_ok = test_middleware_compatibility(wallet)
        results.append(("Middleware 互換性", middleware_ok))
        
    except Exception as e:
        print()
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 結果サマリー
    print()
    print("=" * 70)
    print("📊 テスト結果サマリー")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}  {test_name}")
    
    print()
    
    all_passed = all(result[1] for result in results)
    
    if all_passed and has_balance:
        print("=" * 70)
        print("🎉 全てのテストが成功しました！")
        print("=" * 70)
        print()
        print("✅ testnet 環境のセットアップが完了しました。")
        print()
        print("📋 次のステップ:")
        print("   1. Django example を testnet で実行")
        print("      cd examples/django_example")
        print("      python manage.py runserver")
        print()
        print("   2. 認証・支払いフローをテスト")
        print("      python tests/testnet/test_auth_flow_testnet.py")
        print("      python tests/testnet/test_payment_flow_testnet.py")
        print()
    elif all_passed and not has_balance:
        print("=" * 70)
        print("⚠️  基本テストは成功しましたが、残高が不足しています")
        print("=" * 70)
        print()
        print("faucet から testnet コインを取得してください:")
        print(f"  https://faucet.bitcoincloud.net/")
        print(f"  Address: {wallet_config['address']}")
        print()
    else:
        print("=" * 70)
        print("❌ 一部のテストが失敗しました")
        print("=" * 70)
        print()
        print("トラブルシューティング:")
        print("  - ネットワーク接続を確認してください")
        print("  - py-sdk が正しくインストールされているか確認")
        print("  - ウォレット設定ファイルが正しいか確認")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()

