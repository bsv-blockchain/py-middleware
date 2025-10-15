#!/usr/bin/env python3
"""
BSV Testnet Wallet Creation Script

このスクリプトは testnet 用のウォレットを作成し、設定を保存します。
testnet は無料のテストネットワークなので、実際のコインを使わずに安全にテストできます。
"""

import os
import sys
import json
from pathlib import Path

# py-sdk をインポート
try:
    from bsv.keys import PrivateKey
    from bsv.wallet.wallet_impl import WalletImpl
    from bsv.constants import Network
except ImportError:
    print("❌ Error: py-sdk がインストールされていません")
    print("インストール方法: pip install -e /path/to/py-sdk")
    sys.exit(1)


def create_testnet_wallet(output_dir: str = ".") -> dict:
    """
    testnet 用ウォレットを作成
    
    Args:
        output_dir: 設定ファイルの保存先ディレクトリ
        
    Returns:
        dict: ウォレット情報 (秘密鍵、アドレスなど)
    """
    print("🚀 BSV Testnet ウォレット作成中...")
    print()
    
    # testnet ウォレット作成 (新しい秘密鍵を生成)
    # permission_callback を None にすることで、自動許可
    private_key_obj = PrivateKey()  # ランダムな秘密鍵生成
    wallet = WalletImpl(
        private_key=private_key_obj,
        permission_callback=lambda action: True,  # 全ての操作を自動許可
        load_env=False
    )
    
    # ウォレット情報取得
    private_key = private_key_obj.wif(network=Network.TESTNET)  # WIF 形式 (testnet)
    public_key = private_key_obj.public_key().hex()  # 公開鍵
    address = private_key_obj.address(network=Network.TESTNET)  # testnet アドレス
    
    wallet_info = {
        "network": "testnet",
        "private_key": private_key,
        "public_key": public_key,
        "address": address,
        "created_at": None  # タイムスタンプは後で追加可能
    }
    
    print("✅ Testnet ウォレット作成完了！")
    print()
    print("=" * 70)
    print("📋 ウォレット情報")
    print("=" * 70)
    print(f"🌐 Network:     testnet")
    print(f"📍 Address:     {address}")
    print(f"🔑 Public Key:  {public_key}")
    print(f"🔐 Private Key: {private_key[:20]}...{private_key[-20:]}")
    print("=" * 70)
    print()
    
    # 設定ファイル保存
    output_path = Path(output_dir) / "testnet_wallet_config.json"
    
    # セキュリティ警告
    print("⚠️  セキュリティに関する重要な注意:")
    print("   - 秘密鍵は安全に保管してください")
    print("   - Git リポジトリにコミットしないでください")
    print("   - testnet 専用なので、mainnet では使用しないでください")
    print()
    
    # 保存確認
    save_choice = input(f"設定を {output_path} に保存しますか? (y/n): ").lower().strip()
    
    if save_choice == 'y':
        with open(output_path, 'w') as f:
            json.dump(wallet_info, f, indent=2)
        
        print(f"✅ 設定を保存しました: {output_path}")
        print()
        
        # .gitignore に追加推奨
        gitignore_path = Path(output_dir) / ".gitignore"
        if not gitignore_path.exists():
            print("💡 Tip: .gitignore を作成して秘密鍵を保護することを推奨します")
            create_gitignore = input("   .gitignore を作成しますか? (y/n): ").lower().strip()
            if create_gitignore == 'y':
                with open(gitignore_path, 'w') as f:
                    f.write("# Wallet configurations (contains private keys)\n")
                    f.write("testnet_wallet_config.json\n")
                    f.write("mainnet_wallet_config.json\n")
                    f.write("*.key\n")
                    f.write("*.pem\n")
                print(f"✅ .gitignore を作成しました: {gitignore_path}")
    else:
        print("ℹ️  設定は保存されませんでした")
    
    print()
    print("=" * 70)
    print("📝 次のステップ: testnet コインの取得")
    print("=" * 70)
    print()
    print("testnet ウォレットができました！次は無料の testnet コインを取得します。")
    print()
    print("🌟 BSV Testnet Faucet (無料で testnet コインを取得):")
    print()
    print("1️⃣  Bitcoincloud Faucet")
    print("   URL: https://faucet.bitcoincloud.net/")
    print(f"   Address: {address}")
    print("   → 0.1 tBSV (testnet BSV) を無料で取得できます")
    print()
    print("2️⃣  sCrypt Testnet Faucet")
    print("   URL: https://scrypt.io/faucet/")
    print(f"   Address: {address}")
    print("   → 簡単な認証で testnet コインを取得")
    print()
    print("3️⃣  コイン取得後の確認")
    print("   WhatsOnChain Testnet Explorer:")
    print(f"   https://test.whatsonchain.com/address/{address}")
    print("   → トランザクションと残高を確認できます")
    print()
    print("=" * 70)
    print()
    print("💡 Tips:")
    print("   - testnet コインは無料で価値がありません")
    print("   - 何度でも faucet から取得可能です")
    print("   - エラーが出ても金銭的損失はありません")
    print()
    print("✅ faucet からコインを取得したら、次のスクリプトでテストを実行:")
    print("   python examples/testnet_setup/test_testnet_connection.py")
    print()
    
    return wallet_info


def load_testnet_wallet(config_path: str = "testnet_wallet_config.json"):
    """
    保存された testnet ウォレット設定を読み込んで WalletImpl を作成
    
    Args:
        config_path: 設定ファイルのパス
        
    Returns:
        tuple: (WalletImpl, wallet_info dict)
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(
            f"ウォレット設定ファイルが見つかりません: {config_path}\n"
            f"先に create_testnet_wallet() を実行してウォレットを作成してください"
        )
    
    with open(config_file, 'r') as f:
        wallet_info = json.load(f)
    
    # WIF から秘密鍵を復元
    private_key_obj = PrivateKey(wallet_info['private_key'], network=Network.TESTNET)
    
    # WalletImpl を作成
    wallet = WalletImpl(
        private_key=private_key_obj,
        permission_callback=lambda action: True,  # 全ての操作を自動許可
        load_env=False
    )
    
    print(f"✅ Testnet ウォレット設定を読み込みました: {config_path}")
    print(f"   Address: {wallet_info['address']}")
    
    return wallet, wallet_info


def main():
    """メイン実行"""
    print()
    print("=" * 70)
    print("🌐 BSV Testnet Wallet Creator")
    print("=" * 70)
    print()
    print("このスクリプトは BSV testnet 用のウォレットを作成します。")
    print("testnet は無料のテストネットワークで、実際のコインは不要です。")
    print()
    
    # 出力ディレクトリ
    output_dir = Path(__file__).parent
    
    # ウォレット作成
    try:
        wallet_info = create_testnet_wallet(str(output_dir))
        
        print("=" * 70)
        print("🎉 完了！")
        print("=" * 70)
        print()
        print("次は faucet から testnet コインを取得して、")
        print("test_testnet_connection.py でテストを実行してください。")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

