"""
BSV Middleware - Testnet Integration Tests

このディレクトリには testnet 環境での統合テストが含まれています。

使用方法:
    # 全ての testnet テストを実行
    python -m pytest tests/testnet/ -v
    
    # 特定のテストを実行
    python tests/testnet/test_auth_flow_testnet.py
    python tests/testnet/test_payment_flow_testnet.py

前提条件:
    1. testnet ウォレットを作成
       python examples/testnet_setup/create_testnet_wallet.py
    
    2. testnet コインを取得
       https://faucet.bitcoincloud.net/
    
    3. 接続テストを実行
       python examples/testnet_setup/test_testnet_connection.py

注意:
    - testnet コインは無料で価値がありません
    - エラーが出ても金銭的損失はありません
    - 何度でもテスト可能です
"""

__version__ = "0.1.0"
__all__ = []

