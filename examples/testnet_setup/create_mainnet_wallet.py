#!/usr/bin/env python3
"""
BSV Mainnet Wallet Creation Script

⚠️ 重要な注意事項:
このスクリプトは MAINNET 用のウォレットを作成します。
Mainnet は実際の BSV を使用するため、慎重に扱ってください。

- テストは少額から始めてください
- 秘密鍵は厳重に管理してください
- 本番環境では適切なセキュリティ対策を実施してください
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# py-sdk をインポート
try:
    from bsv.keys import PrivateKey
    from bsv.wallet.wallet_impl import WalletImpl
    from bsv.constants import Network
except ImportError:
    print("❌ Error: py-sdk がインストールされていません")
    print("インストール方法: pip install -e /path/to/py-sdk")
    sys.exit(1)


def create_mainnet_wallet(output_dir: str = ".") -> dict:
    """
    mainnet 用ウォレットを作成
    
    Args:
        output_dir: 設定ファイルの保存先ディレクトリ
        
    Returns:
        dict: ウォレット情報 (秘密鍵、アドレスなど)
    """
    print("=" * 80)
    print("⚠️  MAINNET ウォレット作成 - 重要な警告")
    print("=" * 80)
    print()
    print("これは実際の BSV Mainnet 用のウォレットです。")
    print()
    print("注意事項:")
    print("  ⚠️  実際の BSV (価値のある仮想通貨) を扱います")
    print("  ⚠️  秘密鍵を失うと、コインを永久に失います")
    print("  ⚠️  秘密鍵を他人に知られると、コインが盗まれます")
    print("  ⚠️  必ずバックアップを取り、安全に保管してください")
    print()
    print("推奨事項:")
    print("  ✅ 少額でテストを開始")
    print("  ✅ 秘密鍵は安全な場所に保管")
    print("  ✅ Git リポジトリには絶対にコミットしない")
    print("  ✅ 本番環境では適切なセキュリティ対策を実施")
    print()
    print("=" * 80)
    print()
    
    # ユーザー確認
    confirm = input("上記の内容を理解し、Mainnet ウォレットを作成しますか? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ ウォレット作成を中止しました")
        sys.exit(0)
    
    print()
    print("🚀 BSV Mainnet ウォレット作成中...")
    print()
    
    # mainnet ウォレット作成 (新しい秘密鍵を生成)
    private_key_obj = PrivateKey()  # ランダムな秘密鍵生成
    wallet = WalletImpl(
        private_key=private_key_obj,
        permission_callback=lambda action: True,  # 全ての操作を自動許可
        load_env=False
    )
    
    # ウォレット情報取得
    private_key = private_key_obj.wif(network=Network.MAINNET)  # WIF 形式 (mainnet)
    public_key = private_key_obj.public_key().hex()  # 公開鍵
    address = private_key_obj.address(network=Network.MAINNET)  # mainnet アドレス
    
    wallet_info = {
        "network": "mainnet",
        "private_key": private_key,
        "public_key": public_key,
        "address": address,
        "created_at": datetime.utcnow().isoformat()
    }
    
    print("✅ Mainnet ウォレット作成完了！")
    print()
    print("=" * 80)
    print("📋 ウォレット情報")
    print("=" * 80)
    print(f"🌐 Network:     MAINNET (実際の BSV)")
    print(f"📍 Address:     {address}")
    print(f"🔑 Public Key:  {public_key}")
    print(f"🔐 Private Key: {private_key[:20]}...{private_key[-20:]}")
    print(f"📅 Created:     {wallet_info['created_at']}")
    print("=" * 80)
    print()
    
    # 設定ファイル保存
    output_path = Path(output_dir) / "mainnet_wallet_config.json"
    
    # セキュリティ警告
    print("🔒 セキュリティに関する重要な注意:")
    print("   ⚠️  秘密鍵は絶対に他人に見せないでください")
    print("   ⚠️  Git リポジトリにコミットしないでください")
    print("   ⚠️  安全な場所にバックアップを作成してください")
    print("   ⚠️  この秘密鍵で実際の BSV を管理します")
    print()
    
    # 保存確認
    save_choice = input(f"設定を {output_path} に保存しますか? (y/n): ").lower().strip()
    
    if save_choice == 'y':
        with open(output_path, 'w') as f:
            json.dump(wallet_info, f, indent=2)
        
        # ファイルのパーミッションを制限 (Unix系OSのみ)
        try:
            os.chmod(output_path, 0o600)  # 所有者のみ読み書き可能
            print(f"✅ 設定を保存しました: {output_path}")
            print(f"   (パーミッション: 600 - 所有者のみアクセス可能)")
        except Exception:
            print(f"✅ 設定を保存しました: {output_path}")
        
        print()
        
        # .gitignore に追加推奨
        gitignore_path = Path(output_dir) / ".gitignore"
        if not gitignore_path.exists():
            print("💡 重要: .gitignore を作成して秘密鍵を保護してください")
            create_gitignore = input("   .gitignore を作成しますか? (y/n): ").lower().strip()
            if create_gitignore == 'y':
                with open(gitignore_path, 'w') as f:
                    f.write("# Wallet configurations (contains private keys - NEVER COMMIT)\n")
                    f.write("testnet_wallet_config.json\n")
                    f.write("mainnet_wallet_config.json\n")
                    f.write("client_wallet_config.json\n")
                    f.write("*.key\n")
                    f.write("*.pem\n")
                    f.write("*.wif\n")
                print(f"✅ .gitignore を作成しました: {gitignore_path}")
        else:
            # .gitignore が既に存在する場合、mainnet_wallet_config.json が含まれているか確認
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()
            
            if 'mainnet_wallet_config.json' not in gitignore_content:
                print("⚠️  警告: mainnet_wallet_config.json が .gitignore に含まれていません")
                add_to_gitignore = input("   .gitignore に追加しますか? (y/n): ").lower().strip()
                if add_to_gitignore == 'y':
                    with open(gitignore_path, 'a') as f:
                        f.write("\n# Mainnet wallet configuration (NEVER COMMIT)\n")
                        f.write("mainnet_wallet_config.json\n")
                    print(f"✅ .gitignore に追加しました")
    else:
        print("ℹ️  設定は保存されませんでした")
    
    print()
    print("=" * 80)
    print("📝 次のステップ: BSV の購入と送金")
    print("=" * 80)
    print()
    print("Mainnet ウォレットができました！次は実際の BSV を取得します。")
    print()
    print("🌟 BSV の購入方法:")
    print()
    print("1️⃣  取引所で BSV を購入")
    print("   - HandCash (https://handcash.io/)")
    print("   - Coinbase, Binance などの取引所")
    print()
    print("2️⃣  購入した BSV をこのアドレスに送金")
    print(f"   Address: {address}")
    print()
    print("   ⚠️  少額 (例: 1000 satoshis = 0.00001 BSV) から始めることを強く推奨")
    print()
    print("3️⃣  送金確認")
    print("   WhatsOnChain Mainnet Explorer:")
    print(f"   https://whatsonchain.com/address/{address}")
    print("   → トランザクションと残高を確認できます")
    print()
    print("=" * 80)
    print()
    print("💡 テスト推奨手順:")
    print("   1. 少額 (1000-10000 satoshis) をウォレットに送金")
    print("   2. test_mainnet_payment.py でテスト実行")
    print("   3. 正常動作を確認後、必要に応じて金額を増やす")
    print()
    print("⚠️  重要: 秘密鍵のバックアップを必ず取ってください！")
    print()
    
    return wallet_info


def load_mainnet_wallet(config_path: str = "mainnet_wallet_config.json"):
    """
    保存された mainnet ウォレット設定を読み込んで WalletImpl を作成
    
    Args:
        config_path: 設定ファイルのパス
        
    Returns:
        tuple: (WalletImpl, wallet_info dict)
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(
            f"ウォレット設定ファイルが見つかりません: {config_path}\n"
            f"先に create_mainnet_wallet() を実行してウォレットを作成してください"
        )
    
    with open(config_file, 'r') as f:
        wallet_info = json.load(f)
    
    # ネットワーク確認
    if wallet_info.get('network') != 'mainnet':
        raise ValueError(
            f"このウォレットは {wallet_info.get('network')} 用です。\n"
            f"mainnet 用ウォレットを使用してください。"
        )
    
    # WIF から秘密鍵を復元
    private_key_obj = PrivateKey(wallet_info['private_key'], network=Network.MAINNET)
    
    # WalletImpl を作成
    wallet = WalletImpl(
        private_key=private_key_obj,
        permission_callback=lambda action: True,  # 全ての操作を自動許可
        load_env=False
    )
    
    print(f"✅ Mainnet ウォレット設定を読み込みました: {config_path}")
    print(f"   Network: MAINNET")
    print(f"   Address: {wallet_info['address']}")
    
    return wallet, wallet_info


def main():
    """メイン実行"""
    print()
    print("=" * 80)
    print("🌐 BSV Mainnet Wallet Creator")
    print("=" * 80)
    print()
    
    # 出力ディレクトリ
    output_dir = Path(__file__).parent
    
    # ウォレット作成
    try:
        wallet_info = create_mainnet_wallet(str(output_dir))
        
        print("=" * 80)
        print("🎉 完了！")
        print("=" * 80)
        print()
        print("重要な次のステップ:")
        print("  1. 秘密鍵をバックアップ (印刷、暗号化USBなど)")
        print("  2. 少額の BSV をこのアドレスに送金")
        print("  3. test_mainnet_payment.py でテスト実行")
        print()
        print("⚠️  秘密鍵を失うと、コインを永久に失います！")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()



