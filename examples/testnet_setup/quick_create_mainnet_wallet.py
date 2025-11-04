#!/usr/bin/env python3
"""
Quick Mainnet Wallet Creator - 自動作成版

⚠️ このスクリプトは確認なしでウォレットを作成します
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bsv.keys import PrivateKey
from bsv.wallet.wallet_impl import WalletImpl
from bsv.constants import Network

def create_mainnet_wallet_auto():
    """確認なしでMainnetウォレットを作成"""
    
    print()
    print("=" * 80)
    print("🚀 BSV Mainnet ウォレット作成中...")
    print("=" * 80)
    print()
    
    # Mainnet用の秘密鍵生成
    private_key_obj = PrivateKey()
    
    # ウォレット情報取得
    private_key_wif = private_key_obj.wif(network=Network.MAINNET)
    public_key = private_key_obj.public_key().hex()
    address = private_key_obj.address(network=Network.MAINNET)
    
    wallet_info = {
        "network": "mainnet",
        "private_key": private_key_wif,
        "public_key": public_key,
        "address": address,
        "created_at": datetime.utcnow().isoformat()
    }
    
    print("✅ Mainnet ウォレット作成完了！")
    print()
    print("=" * 80)
    print("📋 ウォレット情報")
    print("=" * 80)
    print(f"🌐 Network:     MAINNET")
    print(f"📍 Address:     {address}")
    print(f"🔑 Public Key:  {public_key[:40]}...")
    print(f"🔐 Private Key: {private_key_wif[:20]}...{private_key_wif[-20:]}")
    print(f"📅 Created:     {wallet_info['created_at']}")
    print("=" * 80)
    print()
    
    # 保存
    output_dir = Path(__file__).parent
    output_path = output_dir / "mainnet_wallet_config.json"
    
    with open(output_path, 'w') as f:
        json.dump(wallet_info, f, indent=2)
    
    # パーミッション設定
    try:
        os.chmod(output_path, 0o600)
        print(f"✅ 設定を保存しました: {output_path}")
        print(f"   (パーミッション: 600 - 所有者のみアクセス可能)")
    except Exception:
        print(f"✅ 設定を保存しました: {output_path}")
    
    print()
    print("=" * 80)
    print("💰 次のステップ: BSV を送金")
    print("=" * 80)
    print()
    print("📍 送金先アドレス:")
    print()
    print(f"   {address}")
    print()
    print("💡 推奨送金額:")
    print(f"   10,000 - 100,000 satoshis (0.0001 - 0.001 BSV)")
    print(f"   約 $0.005 - $0.05 (at $50/BSV)")
    print()
    print("🌟 送金方法:")
    print(f"   1. HandCash: https://handcash.io/")
    print(f"   2. 取引所: Coinbase, Binance等")
    print()
    print("📊 送金確認:")
    print(f"   WhatsOnChain: https://whatsonchain.com/address/{address}")
    print()
    print("=" * 80)
    print()
    print("⚠️  重要:")
    print("   - 秘密鍵をバックアップしてください")
    print("   - Git にコミットしないでください")
    print("   - 少額から始めてください")
    print()
    
    return wallet_info


if __name__ == "__main__":
    try:
        wallet_info = create_mainnet_wallet_auto()
        
        print("=" * 80)
        print("🎉 完了！")
        print("=" * 80)
        print()
        print(f"送金先アドレス: {wallet_info['address']}")
        print()
        print("送金後、以下のコマンドでテストを実行:")
        print("  python tests/testnet/test_mainnet_payment.py")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)











