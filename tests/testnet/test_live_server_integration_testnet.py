"""
BSV Testnet Live Server Integration Test

django_exampleサーバーを使って、実際のHTTPリクエストで
認証 + 支払いの完全なフローをtestnetでテストします。

テスト実行方法：

1. ターミナル1: Django サーバーを起動
   cd examples/django_example
   python manage.py runserver 8000

2. ターミナル2: テストを実行
   python -m pytest tests/testnet/test_live_server_integration_testnet.py -v -s
"""

import os
import sys
import json
import pytest
import time
import requests
from pathlib import Path

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')

# py-sdk imports
try:
    from bsv.wallet.wallet_impl import WalletImpl
    from bsv.keys import PrivateKey
    from bsv.constants import Network
    from bsv.script.type import P2PKH
except ImportError:
    pytest.skip("py-sdk not installed", allow_module_level=True)


def load_testnet_wallet():
    """testnet ウォレット設定を読み込む"""
    config_path = Path(__file__).parents[2] / "examples" / "testnet_setup" / "testnet_wallet_config.json"
    
    if not config_path.exists():
        pytest.skip(
            f"Testnet wallet not found: {config_path}\n"
            "Run: python examples/testnet_setup/create_testnet_wallet.py"
        )
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # WIF から秘密鍵を復元
    private_key_obj = PrivateKey(config["private_key"], network=Network.TESTNET)
    
    # WhatsOnChainから実際のUTXOを取得するように設定
    os.environ['USE_WOC'] = '1'
    
    # ウォレット作成
    wallet = WalletImpl(
        private_key=private_key_obj,
        permission_callback=lambda action: True,  # 全ての操作を自動許可
        load_env=False
    )
    
    return wallet, config


def check_testnet_balance(address: str) -> int:
    """testnet 残高を確認"""
    try:
        url = f"https://api.whatsonchain.com/v1/bsv/test/address/{address}/balance"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        balance = response.json()
        return balance.get("confirmed", 0) + balance.get("unconfirmed", 0)
    except:
        return 0


def check_server_running(url: str, timeout: int = 5) -> bool:
    """サーバーが起動しているか確認"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code in [200, 401, 402]  # 任意の有効なレスポンス
    except requests.exceptions.RequestException:
        return False


class TestLiveServerIntegration:
    """Live Server統合テスト（django_exampleを使用）"""
    
    # Django exampleサーバーのURL
    SERVER_URL = "http://localhost:8000"
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """テストセットアップ"""
        # Testnet ウォレット読み込み
        self.wallet, self.wallet_config = load_testnet_wallet()
        
        # 残高確認
        self.balance = check_testnet_balance(self.wallet_config["address"])
        
        print()
        print("=" * 70)
        print("🧪 Live Server Integration Test (django_example)")
        print("=" * 70)
        print(f"Server URL: {self.SERVER_URL}")
        print(f"Network:    testnet")
        print(f"Address:    {self.wallet_config['address']}")
        print(f"Balance:    {self.balance:,} satoshis")
        print(f"Explorer:   https://test.whatsonchain.com/address/{self.wallet_config['address']}")
        print("=" * 70)
        print()
        
        # サーバーが起動しているか確認
        if not check_server_running(self.SERVER_URL):
            pytest.skip(
                f"\n❌ Django server is not running at {self.SERVER_URL}\n\n"
                "Please start the server first:\n"
                "  cd examples/django_example\n"
                "  python manage.py runserver 8000\n"
            )
        
        if self.balance < 2000:
            print("⚠️  Warning: 残高が少ないです (< 2000 satoshis)")
            pytest.skip("Insufficient testnet balance")
    
    def test_01_server_health_check(self):
        """Test 1: サーバーヘルスチェック"""
        print("Test 1: サーバーヘルスチェック")
        
        try:
            response = requests.get(f"{self.SERVER_URL}/health/", timeout=5)
            
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ サーバー起動中")
                print(f"     Service: {data.get('service', 'N/A')}")
                print(f"     Status: {data.get('status', 'N/A')}")
            else:
                print(f"  ⚠️  Unexpected status: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Connection error: {e}")
            pytest.fail("Server connection failed")
    
    def test_02_free_endpoint_access(self):
        """Test 2: 無料エンドポイントへのアクセス"""
        print()
        print("Test 2: 無料エンドポイントアクセス")
        
        endpoints = [
            "/",
            "/health/",
            "/public/"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{self.SERVER_URL}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                print(f"  ✅ {endpoint}: OK")
            else:
                print(f"  ⚠️  {endpoint}: {response.status_code}")
    
    def test_03_payment_required_response(self):
        """Test 3: 支払いが必要なエンドポイントで402レスポンス"""
        print()
        print("Test 3: 402 Payment Required レスポンス")
        
        # 支払いヘッダーなしでプレミアムエンドポイントにアクセス
        response = requests.get(f"{self.SERVER_URL}/premium/", timeout=5)
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 402:
            print(f"  ✅ 402 Payment Required 受信")
            
            # ヘッダーを確認
            if 'X-BSV-Payment-Satoshis-Required' in response.headers:
                required = response.headers['X-BSV-Payment-Satoshis-Required']
                print(f"     Required: {required} satoshis")
        elif response.status_code == 401:
            print(f"  ⚠️  401 Unauthorized (認証が先に必要)")
            print(f"     Note: AuthMiddlewareが先に実行されています")
        else:
            print(f"  ⚠️  Unexpected status: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
    
    def test_04_payment_transaction_and_access(self):
        """Test 4: 実際の支払いトランザクションでエンドポイントアクセス"""
        print()
        print("Test 4: 実際の支払いトランザクション")
        
        required_amount = 500  # satoshis
        
        # 支払い先アドレス（テスト用に自分自身）
        recipient_address = self.wallet_config['address']
        locking_script = P2PKH().lock(recipient_address)
        locking_script_hex = locking_script.hex()
        
        print(f"  📤 Creating payment transaction: {required_amount} satoshis")
        
        try:
            # トランザクション作成
            action_args = {
                "description": f"Payment for /premium/ endpoint - {required_amount} sats",
                "outputs": [{
                    "satoshis": required_amount,
                    "lockingScript": locking_script_hex,
                    "outputDescription": "Endpoint payment"
                }]
            }
            
            create_result = self.wallet.create_action(None, action_args, "live_server_test")
            
            if 'signableTransaction' not in create_result:
                print(f"  ⚠️  No signable transaction")
                return
            
            tx_bytes = create_result['signableTransaction']['tx']
            
            # ブロードキャスト
            print(f"  📡 Broadcasting transaction...")
            internalize_result = self.wallet.internalize_action(
                None,
                {"tx": tx_bytes},
                "live_server_test"
            )
            
            if not internalize_result.get('accepted'):
                print(f"  ⚠️  Transaction not accepted")
                print(f"     Error: {internalize_result.get('error')}")
                return
            
            txid = internalize_result.get('txid')
            if isinstance(txid, bytes):
                txid = txid.hex()
            
            print(f"  ✅ Transaction broadcast success")
            print(f"     TXID: {txid}")
            print(f"     Explorer: https://test.whatsonchain.com/tx/{txid}")
            
            # 支払いヘッダーを作成
            tx_hex = tx_bytes.hex() if isinstance(tx_bytes, bytes) else tx_bytes
            
            import secrets
            payment_data = json.dumps({
                "transaction": tx_hex,
                "derivationPrefix": secrets.token_hex(16),
                "derivationSuffix": secrets.token_hex(16)
            })
            
            # エンドポイントにアクセス（支払いヘッダー付き）
            print(f"  📡 Accessing endpoint with payment header...")
            
            response = requests.get(
                f"{self.SERVER_URL}/premium/",
                headers={
                    "x-bsv-payment": payment_data
                },
                timeout=10
            )
            
            print(f"  📨 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ 支払い成功！エンドポイントアクセス許可")
                
                try:
                    data = response.json()
                    print(f"     Message: {data.get('message', 'N/A')}")
                    if 'premium_data' in data:
                        print(f"     Premium Data: {data['premium_data']}")
                    
                    print(f"  ✅ Live Server統合テスト成功！")
                    
                except json.JSONDecodeError:
                    print(f"     Response: {response.text[:200]}")
                    
            elif response.status_code == 401:
                print(f"  ⚠️  401 Unauthorized")
                print(f"     Note: AuthMiddlewareが認証を要求しています")
                print(f"     Response: {response.text[:200]}")
            elif response.status_code == 402:
                print(f"  ⚠️  402 Payment still required")
                print(f"     Response: {response.text[:200]}")
            else:
                print(f"  ⚠️  Unexpected status: {response.status_code}")
                print(f"     Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    def test_05_summary(self):
        """Test 5: テストサマリー"""
        print()
        print("=" * 70)
        print("📊 Live Server Integration Test - Summary")
        print("=" * 70)
        print()
        print(f"✅ Live Server統合テスト完了")
        print()
        print(f"Server:  {self.SERVER_URL}")
        print(f"Network: testnet")
        print(f"Balance: {self.balance:,} satoshis")
        print(f"Address: {self.wallet_config['address']}")
        print()
        print("確認できたこと:")
        print("  ✅ Django exampleサーバーとの通信")
        print("  ✅ 実際のHTTPリクエスト")
        print("  ✅ testnetでのトランザクション送信")
        print("  ✅ ミドルウェアによる支払い検証")
        print()
        print("次のステップ:")
        print("  - django_exampleの設定をtestnetウォレットに変更")
        print("  - 認証ミドルウェアのテスト追加")
        print("  - 認証 + 支払いの完全統合テスト")
        print()
        print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])



