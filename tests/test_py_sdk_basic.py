"""
py-sdk feature/auth/certificates-port ブランチの基本動作テスト

Phase 2.1 Day 1: py-sdk 動作確認
このテストファイルは py-sdk との統合で最初に実行するテストです。
"""

import pytest
import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class TestPySdkBasicIntegration:
    """py-sdk 基本統合テスト"""
    
    def test_py_sdk_imports(self):
        """
        py-sdk 認証モジュールのインポート確認
        
        このテストでは feature/auth/certificates-port ブランチの
        基本的なクラスがインポートできるかを確認します。
        """
        print("\n=== py-sdk Import Test ===")
        
        try:
            # 基本的な認証関連クラスのインポート
            from bsv.auth.peer import Peer, PeerOptions
            print("✅ Peer, PeerOptions imported successfully")
            
            from bsv.auth.transports.transport import Transport  
            print("✅ Transport imported successfully")
            
            from bsv.auth.session_manager import SessionManager
            print("✅ SessionManager imported successfully")
            
            from bsv.wallet.wallet_interface import WalletInterface
            print("✅ WalletInterface imported successfully")
            
            from bsv.auth.verifiable_certificate import VerifiableCertificate
            print("✅ VerifiableCertificate imported successfully")
            
            print("🎉 All py-sdk auth modules loaded successfully!")
            return True
            
        except ImportError as e:
            print(f"❌ py-sdk import failed: {e}")
            logger.error(f"py-sdk import error: {e}")
            
            # 詳細なエラー情報を記録
            self._log_import_error(e)
            pytest.fail(f"py-sdk import error: {e}")
            
    def test_peer_options_creation(self):
        """PeerOptions の基本作成テスト"""
        print("\n=== PeerOptions Creation Test ===")
        
        try:
            from bsv.auth.peer import PeerOptions
            
            # 基本的な PeerOptions 作成
            options = PeerOptions()
            print("✅ Basic PeerOptions creation successful")
            
            # 引数付き作成テスト
            options_with_args = PeerOptions(
                wallet=None,  # まずは None で
                transport=None,
                certificates_to_request=None,
                session_manager=None
            )
            print("✅ PeerOptions with arguments creation successful")
            
        except Exception as e:
            print(f"❌ PeerOptions creation failed: {e}")
            logger.error(f"PeerOptions creation error: {e}")
            self._log_integration_error("PeerOptions Creation", e)
            pytest.fail(f"PeerOptions error: {e}")

    def test_transport_interface(self):
        """Transport インターフェースの確認"""
        print("\n=== Transport Interface Test ===")
        
        try:
            from bsv.auth.transports.transport import Transport
            
            # Transport は ABC なので直接インスタンス化はできない
            # インターフェースの確認のみ
            assert hasattr(Transport, 'send'), "Transport.send method not found"
            assert hasattr(Transport, 'on_data'), "Transport.on_data method not found"
            
            print("✅ Transport interface methods available")
            
            # メソッドシグネチャの確認
            import inspect
            send_sig = inspect.signature(Transport.send)
            on_data_sig = inspect.signature(Transport.on_data)
            
            print(f"Transport.send signature: {send_sig}")
            print(f"Transport.on_data signature: {on_data_sig}")
            
        except Exception as e:
            print(f"❌ Transport interface check failed: {e}")
            logger.error(f"Transport interface error: {e}")
            self._log_integration_error("Transport Interface", e)
            pytest.fail(f"Transport interface error: {e}")

    def test_session_manager_creation(self):
        """SessionManager の基本作成テスト"""
        print("\n=== SessionManager Creation Test ===")
        
        try:
            from bsv.auth.session_manager import SessionManager
            
            # SessionManager 作成テスト
            session_mgr = SessionManager()
            print("✅ SessionManager creation successful")
            
            # 基本メソッドの存在確認
            expected_methods = ['has_session', 'get_session', 'create_session']
            for method in expected_methods:
                if hasattr(session_mgr, method):
                    print(f"✅ SessionManager.{method} method available")
                else:
                    print(f"⚠️ SessionManager.{method} method not found")
            
        except Exception as e:
            print(f"❌ SessionManager creation failed: {e}")
            logger.error(f"SessionManager creation error: {e}")
            self._log_integration_error("SessionManager Creation", e)
            pytest.fail(f"SessionManager error: {e}")

    def test_wallet_interface_inspection(self):
        """WalletInterface の構造確認"""
        print("\n=== WalletInterface Inspection Test ===")
        
        try:
            from bsv.wallet.wallet_interface import WalletInterface
            import inspect
            
            # WalletInterface の抽象メソッドを確認
            abstract_methods = getattr(WalletInterface, '__abstractmethods__', set())
            print(f"WalletInterface abstract methods: {list(abstract_methods)}")
            
            # 重要なメソッドの存在確認
            important_methods = [
                'get_public_key', 'create_signature', 'internalize_action',
                'encrypt', 'decrypt'
            ]
            
            for method in important_methods:
                if hasattr(WalletInterface, method):
                    sig = inspect.signature(getattr(WalletInterface, method))
                    print(f"✅ WalletInterface.{method}{sig}")
                else:
                    print(f"❌ WalletInterface.{method} not found")
            
        except Exception as e:
            print(f"❌ WalletInterface inspection failed: {e}")
            logger.error(f"WalletInterface inspection error: {e}")
            self._log_integration_error("WalletInterface Inspection", e)
            pytest.fail(f"WalletInterface error: {e}")

    def test_current_middleware_imports(self):
        """既存のmiddleware クラスのインポート確認"""
        print("\n=== Current Middleware Import Test ===")
        
        try:
            from bsv_middleware.django.auth_middleware import BSVAuthMiddleware
            print("✅ BSVAuthMiddleware imported successfully")
            
            from bsv_middleware.py_sdk_bridge import PySdkBridge
            print("✅ PySdkBridge imported successfully")
            
            from tests.settings import MockTestWallet
            print("✅ MockTestWallet imported successfully")
            
            # MockTestWallet の基本メソッド確認
            wallet = MockTestWallet()
            assert hasattr(wallet, 'sign_message'), "MockTestWallet.sign_message not found"
            assert hasattr(wallet, 'get_public_key'), "MockTestWallet.get_public_key not found"
            assert hasattr(wallet, 'internalize_action'), "MockTestWallet.internalize_action not found"
            
            print("✅ MockTestWallet methods available")
            
        except Exception as e:
            print(f"❌ Current middleware import failed: {e}")
            logger.error(f"Current middleware import error: {e}")
            self._log_integration_error("Current Middleware Import", e)
            pytest.fail(f"Current middleware import error: {e}")

    def _log_import_error(self, error: Exception):
        """インポートエラーの詳細記録"""
        error_details = {
            'error_type': 'ImportError',
            'error_message': str(error),
            'affected_module': 'py-sdk auth modules',
            'phase': 'Phase 2.1 Day 1',
            'test': 'py-sdk imports'
        }
        
        # エラーログファイルに記録
        self._write_error_log(error_details)

    def _log_integration_error(self, test_name: str, error: Exception):
        """統合エラーの詳細記録"""
        import traceback
        
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'test_name': test_name,
            'phase': 'Phase 2.1 Day 1',
            'traceback': traceback.format_exc()
        }
        
        # エラーログファイルに記録
        self._write_error_log(error_details)

    def _write_error_log(self, error_details: dict):
        """エラーログファイルに書き込み"""
        import json
        from datetime import datetime
        
        error_details['timestamp'] = datetime.now().isoformat()
        
        log_file = project_root / 'integration_errors.log'
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(error_details, indent=2) + '\n\n')
        except Exception as e:
            print(f"Failed to write error log: {e}")


if __name__ == "__main__":
    """直接実行時のテスト"""
    print("🚀 Starting py-sdk Basic Integration Tests...")
    
    test_instance = TestPySdkBasicIntegration()
    
    tests = [
        test_instance.test_py_sdk_imports,
        test_instance.test_peer_options_creation,
        test_instance.test_transport_interface,
        test_instance.test_session_manager_creation,
        test_instance.test_wallet_interface_inspection,
        test_instance.test_current_middleware_imports
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
            print(f"✅ {test.__name__} PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED: {e}")
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Ready for Day 2.")
    else:
        print("⚠️ Some tests failed. Check integration_errors.log for details.")
