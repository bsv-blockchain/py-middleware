"""
MockTestWallet を py-sdk WalletInterface に適合させるアダプター

このモジュールは、簡単なwallet (MockTestWallet) を py-sdk の複雑な
WalletInterface に適合させるためのアダプター層を提供します。

Phase 2.1 Day 2: 実際の統合実装
"""

from typing import Any, Dict, TYPE_CHECKING
import logging

# Import WalletInterface with proper type checking support
PY_SDK_AVAILABLE = False  # Initialize before conditional import

if TYPE_CHECKING:
    # For type checking, always import the real type
    from bsv.wallet.wallet_interface import WalletInterface
else:
    # At runtime, try to import, fall back to Any if not available
    try:
        from bsv.wallet.wallet_interface import WalletInterface
        PY_SDK_AVAILABLE = True
    except ImportError:
        # Use Any for runtime when py-sdk is not available
        WalletInterface = Any  # type: ignore
        PY_SDK_AVAILABLE = False

logger = logging.getLogger(__name__)


class MiddlewareWalletAdapter(WalletInterface):
    """
    Django middleware 用の WalletInterface アダプター
    
    簡単なwallet (MockTestWallet) を py-sdk の複雑な
    WalletInterface に適合させます。
    
    Args:
        simple_wallet: MockTestWallet や他の簡単なwallet実装
    """
    
    def __init__(self, simple_wallet: Any) -> None:
        self.simple_wallet = simple_wallet
        logger.debug(f"WalletAdapter initialized with {type(simple_wallet).__name__}")
    
    # === 重要なメソッド (middleware で使用) ===
    
    def get_public_key(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """
        py-sdk format: get_public_key(ctx, args, originator)
        simple format: get_public_key() -> str
        
        Returns object with public_key attribute (py-sdk Peer expects this)
        """
        try:
            pub_key_hex = self.simple_wallet.get_public_key()
            
            # Create object with public_key attribute for py-sdk Peer compatibility
            from bsv.keys import PublicKey
            pub_key_obj = PublicKey(pub_key_hex)
            
            class PublicKeyResult:
                def __init__(self, hex_key: str, pub_key_obj: Any) -> None:
                    self.publicKey = hex_key  # for test compatibility
                    self.public_key = pub_key_obj  # for py-sdk Peer compatibility
                    self.hex = hex_key
                    
                def __contains__(self, item: str) -> bool:
                    # Support 'publicKey' in result for test compatibility
                    return item in ['publicKey', 'public_key', 'hex']
                
                def __getitem__(self, key: str) -> Any:
                    # Support result['publicKey'] for test compatibility
                    if key == 'publicKey':
                        return self.publicKey
                    elif key == 'public_key':
                        return self.public_key
                    elif key == 'hex':
                        return self.hex
                    raise KeyError(key)
            
            result = PublicKeyResult(pub_key_hex, pub_key_obj)
            logger.debug(f"get_public_key: returning object with public_key.hex()={pub_key_obj.hex()[:20]}...")
            return result
        except Exception as e:
            logger.error(f"get_public_key error: {e}")
            raise
    
    def create_signature(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """
        py-sdk format: create_signature(ctx, args, originator)
        simple format: sign_message(message: bytes) -> bytes
        
        py-sdk expects specific args format for signatures
        """
        try:
            logger.debug(f"create_signature called with args: {args}")
            
            # py-sdkでは複雑な引数構造を使用
            encryption_args = args.get('encryption_args', {})
            protocol_id = encryption_args.get('protocol_id', {})
            protocol_name = protocol_id.get('protocol_name', '')
            
            # signature_alg に基づいて処理
            signature_alg = protocol_id.get('signature_alg', '')
            
            # データを取得（複数の可能な場所）
            message = args.get('data', b'')
            if not message:
                message = args.get('message', b'')
            if not message:
                # 直接バイト配列として提供される場合
                message = encryption_args.get('data', b'')
            
            if isinstance(message, str):
                message = message.encode('utf-8')
            elif isinstance(message, (list, tuple)):
                # byte array の場合
                message = bytes(message)
                
            logger.debug(f"create_signature: protocol={protocol_name}, message_len={len(message)}")
            
            if not message:
                raise ValueError("No message data found in args")
                
            signature = self.simple_wallet.sign_message(message)
            
            # Return object with signature attribute for py-sdk Peer compatibility
            class SignatureResult:
                def __init__(self, sig: bytes, alg: str, proto: str) -> None:
                    self.signature = sig  # for py-sdk Peer compatibility
                    self.algorithm = alg
                    self.protocol = proto
                    
                def __contains__(self, item: str) -> bool:
                    # Support 'signature' in result for test compatibility
                    return item in ['signature', 'algorithm', 'protocol']
                
                def __getitem__(self, key: str) -> Any:
                    # Support result['signature'] for test compatibility
                    if key == 'signature':
                        return self.signature
                    elif key == 'algorithm':
                        return self.algorithm
                    elif key == 'protocol':
                        return self.protocol
                    raise KeyError(key)
            
            result = SignatureResult(signature, signature_alg or 'ECDSA_secp256k1', protocol_name)
            logger.debug(f"create_signature result: signature_len={len(signature)}")
            return result
            
        except Exception as e:
            logger.error(f"create_signature error: {e}")
            logger.error(f"create_signature args: {args}")
            import traceback
            traceback.print_exc()
            raise
    
    def internalize_action(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """
        py-sdk format: internalize_action(ctx, args, originator)
        simple format: internalize_action(action: dict) -> dict
        
        支払い処理で使用される重要なメソッド
        """
        try:
            # args から action データを取得
            action = args.get('action', {})
            if not action:
                # args 自体が action の場合
                action = args
                
            logger.debug(f"internalize_action: action={action}")
            result = self.simple_wallet.internalize_action(action)
            
            # py-sdk 期待形式に変換
            py_sdk_result = {
                'accepted': result.get('accepted', True),
                'satoshisPaid': result.get('satoshisPaid', 0),
                'transactionId': result.get('transactionId', 'unknown')
            }
            
            logger.debug(f"internalize_action result: {py_sdk_result}")
            return py_sdk_result
        except Exception as e:
            logger.error(f"internalize_action error: {e}")
            raise
    
    # === その他の必須抽象メソッド (基本実装) ===
    
    def encrypt(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """暗号化 - 現在の簡単なウォレットでは未実装"""
        logger.warning("encrypt method called but not implemented in simple wallet")
        raise NotImplementedError("encrypt not implemented in simple wallet")
    
    def decrypt(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """復号化 - 現在の簡単なウォレットでは未実装"""
        logger.warning("decrypt method called but not implemented in simple wallet")
        raise NotImplementedError("decrypt not implemented in simple wallet")
    
    def create_hmac(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """HMAC作成 - 基本的な署名で代用"""
        logger.warning("create_hmac called, using signature instead")
        return self.create_signature(ctx, args, originator)
    
    def verify_hmac(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """HMAC検証 - 簡易実装"""
        logger.warning("verify_hmac called, returning True (simplified)")
        return {'valid': True}
    
    def verify_signature(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """署名検証 - 簡易実装"""
        logger.debug("verify_signature called")
        return {'valid': True}
    
    # === Wallet操作系メソッド ===
    
    def create_action(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """アクション作成 - 簡易実装"""
        logger.debug(f"create_action: args={args}")
        return {
            'action': args,
            'status': 'created',
            'actionId': 'mock_action_id'
        }
    
    def sign_action(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """アクション署名 - 簡易実装"""
        logger.debug(f"sign_action: args={args}")
        return {
            'signed': True,
            'actionId': args.get('actionId', 'unknown')
        }
    
    def abort_action(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """アクション中止 - 簡易実装"""
        logger.debug(f"abort_action: args={args}")
        return {'aborted': True}
    
    def list_actions(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """アクション一覧 - 空リスト返却"""
        return {'actions': []}
    
    def list_outputs(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """出力一覧 - 空リスト返却"""
        return {'outputs': []}
    
    def relinquish_output(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """出力放棄 - 簡易実装"""
        return {'relinquished': True}
    
    # === 鍵関連メソッド ===
    
    def reveal_counterparty_key_linkage(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """相手方キーリンケージ開示 - 未実装"""
        raise NotImplementedError("reveal_counterparty_key_linkage not implemented")
    
    def reveal_specific_key_linkage(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """特定キーリンケージ開示 - 未実装"""
        raise NotImplementedError("reveal_specific_key_linkage not implemented")
    
    # === 証明書関連メソッド ===
    
    def acquire_certificate(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """証明書取得 - 未実装"""
        logger.warning("acquire_certificate called but not implemented")
        return {'certificate': None}
    
    def list_certificates(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """証明書一覧 - 空リスト返却"""
        return {'certificates': []}
    
    def prove_certificate(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """証明書証明 - 簡易実装"""
        return {'proof': 'mock_proof'}
    
    def relinquish_certificate(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """証明書放棄 - 簡易実装"""
        return {'relinquished': True}
    
    # === 検索・発見メソッド ===
    
    def discover_by_identity_key(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """Identity Key による発見 - 簡易実装"""
        identity_key = args.get('identityKey', 'unknown')
        return {'found': False, 'identityKey': identity_key}
    
    def discover_by_attributes(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """属性による発見 - 簡易実装"""
        return {'found': False, 'attributes': args.get('attributes', {})}
    
    # === 認証関連メソッド ===
    
    def is_authenticated(self, ctx: Any, args: Any, originator: str) -> Any:
        """認証状態確認 - 常にTrue返却"""
        return {'authenticated': True}
    
    def wait_for_authentication(self, ctx: Any, args: Any, originator: str) -> Any:
        """認証待機 - 即座に認証済み返却"""
        return {'authenticated': True}
    
    # === ネットワーク情報メソッド ===
    
    def get_height(self, ctx: Any, args: Any, originator: str) -> Any:
        """ブロック高取得 - モック値返却"""
        return {'height': 800000}
    
    def get_header_for_height(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """指定高のヘッダー取得 - モック値返却"""
        height = args.get('height', 800000)
        return {
            'height': height,
            'header': 'mock_header_data'
        }
    
    def get_network(self, ctx: Any, args: Any, originator: str) -> Any:
        """ネットワーク情報取得 - mainnet返却"""
        return {'network': 'mainnet'}
    
    def get_version(self, ctx: Any, args: Any, originator: str) -> Any:
        """バージョン情報取得"""
        return {
            'version': '1.0.0',
            'adapter': 'MiddlewareWalletAdapter'
        }


class WalletImplAdapter:
    """
    Lightweight adapter for WalletImpl to convert get_public_key response format.
    WalletImpl returns Dict, but Peer expects object with public_key attribute.
    """
    def __init__(self, wallet_impl: Any):
        self.wallet_impl = wallet_impl
        logger.debug("Created WalletImplAdapter")
    
    def get_public_key(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """Convert WalletImpl Dict response to object with public_key attribute."""
        result = self.wallet_impl.get_public_key(ctx, args, originator)
        
        if isinstance(result, dict):
            if 'error' in result:
                raise Exception(result['error'])
            
            pub_key_hex = result.get('publicKey') or result.get('public_key')
            if pub_key_hex:
                from bsv.keys import PublicKey
                pub_key_obj = PublicKey(pub_key_hex)
                
                class PublicKeyResult:
                    def __init__(self, hex_key: str, pub_key_obj: Any):
                        self.publicKey = hex_key
                        self.public_key = pub_key_obj
                        self.hex = hex_key
                
                return PublicKeyResult(pub_key_hex, pub_key_obj)
        
        return result
    
    def create_signature(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """
        Convert WalletImpl Dict response to object with signature attribute.
        Transforms nested encryption_args structure to BRC-100 compliant flat structure.
        """
        # BRC-100 compliant: Convert nested encryption_args to flat structure
        enc_args = args.get('encryption_args', {})
        if enc_args:
            # Flatten the structure for BRC-100 compliance (snake_case)
            flat_args = {
                'protocol_id': enc_args.get('protocol_id'),
                'key_id': enc_args.get('key_id'),
                'counterparty': enc_args.get('counterparty'),
                'data': args.get('data'),
                'hash_to_directly_sign': args.get('hash_to_directly_sign'),
            }
            
            # Normalize counterparty type to py-sdk/go definitions
            # CounterpartyType: ANYONE=1, SELF=2, OTHER=3
            try:
                cp = flat_args.get('counterparty')
                if isinstance(cp, dict):
                    # If no type and a counterparty pubkey is present, assume OTHER=3
                    if 'type' not in cp and ('counterparty' in cp and cp['counterparty']):
                        cp['type'] = 3
                else:
                    # If provided as hex/pubkey, wrap as OTHER=3
                    flat_args['counterparty'] = {'type': 3, 'counterparty': cp}
            except Exception as e:
                logger.debug(f"create_signature type fixing failed: {e}")
            
            args = flat_args
        
        result = self.wallet_impl.create_signature(ctx, args, originator)
        
        if isinstance(result, dict):
            if 'error' in result:
                logger.error(f"create_signature error: {result['error']}")
                raise Exception(result['error'])
            
            signature = result.get('signature')
            if signature:
                class SignatureResult:
                    def __init__(self, sig: bytes):
                        self.signature = sig
                
                return SignatureResult(signature)
        
        return result
    
    def verify_signature(self, ctx: Any, args: Dict[str, Any], originator: str) -> Any:
        """
        Normalize verify_signature arguments to BRC-100 compliant flat structure.
        Transforms nested encryption_args to flat snake_case structure.
        """
        print(f"[ADAPTER] verify_signature called! originator={originator}")
        
        # BRC-100 compliant: Convert nested encryption_args to flat structure
        enc_args = args.get('encryption_args', {})
        if enc_args:
            # Flatten the structure for BRC-100 compliance (snake_case)
            flat_args = {
                'protocol_id': enc_args.get('protocol_id'),
                'key_id': enc_args.get('key_id'),
                'counterparty': enc_args.get('counterparty'),
                'for_self': enc_args.get('for_self', False),
                'data': args.get('data'),
                'hash_to_directly_verify': args.get('hash_to_directly_verify'),
                'signature': args.get('signature'),
            }
            # Normalize counterparty type to py-sdk/go definitions (ANYONE=1, SELF=2, OTHER=3)
            try:
                cp = flat_args.get('counterparty')
                if isinstance(cp, dict):
                    if 'type' not in cp and ('counterparty' in cp and cp['counterparty']):
                        cp['type'] = 3
                else:
                    flat_args['counterparty'] = {'type': 3, 'counterparty': cp}
            except Exception as e:
                logger.debug(f"verify_signature type fixing failed: {e}")
            args = flat_args
        
        # Debug: log flattened arguments
        try:
            proto_debug = args.get('protocol_id', {})
            print(f"[ADAPTER DEBUG] protocol: {proto_debug.get('protocol', proto_debug) if isinstance(proto_debug, dict) else proto_debug}")
            print(f"[ADAPTER DEBUG] key_id: {str(args.get('key_id', 'NONE'))[:50]}...")
            cp_debug = args.get('counterparty', {})
            print(f"[ADAPTER DEBUG] counterparty.type: {cp_debug.get('type', 'NONE') if isinstance(cp_debug, dict) else 'NONE'}")
        except Exception as e:
            print(f"[ADAPTER DEBUG] Failed to log args: {e}")
        
        # Call underlying verify_signature and wrap result as object
        result = self.wallet_impl.verify_signature(ctx, args, originator)
        print(f"[ADAPTER VERIFY] WalletImpl.verify_signature result: {result}")
        
        if isinstance(result, dict):
            # Convert dict to object with .valid attribute (Peer expects object)
            class VerifyResult:
                def __init__(self, valid: bool, error: str = None):
                    self.valid = valid
                    self.error = error
            
            if 'error' in result:
                print(f"[ADAPTER VERIFY] verify_signature error: {result['error']}")
                return VerifyResult(False, result['error'])
            
            valid = result.get('valid', False)
            print(f"[ADAPTER VERIFY] signature verification: {valid}")
            print(f"[ADAPTER VERIFY] returning VerifyResult with valid={valid}")
            return VerifyResult(valid)
        
        return result

    def __getattr__(self, name: str) -> Any:
        """Delegate all other methods to the wrapped WalletImpl."""
        return getattr(self.wallet_impl, name)


def create_wallet_adapter(simple_wallet: Any) -> Any:
    """
    簡単なウォレットから py-sdk 互換のウォレットアダプターを作成
    
    Args:
        simple_wallet: MockTestWallet などの簡単なウォレット実装、または WalletImpl
        
    Returns:
        py-sdk WalletInterface 互換のアダプター
    """
    if not PY_SDK_AVAILABLE:
        logger.warning("py-sdk not available, returning wrapper without WalletInterface inheritance")
        # py-sdk が無い場合は簡易ラッパーを返す
        return simple_wallet  # type: ignore
    
    # Check if wallet is already a full WalletImpl (has create_action, internalize_action, etc.)
    if hasattr(simple_wallet, 'create_action') and hasattr(simple_wallet, 'internalize_action'):
        logger.debug("Wallet is WalletImpl, wrapping with WalletImplAdapter")
        return WalletImplAdapter(simple_wallet)
    
    # Otherwise, wrap it with full adapter
    return MiddlewareWalletAdapter(simple_wallet)
