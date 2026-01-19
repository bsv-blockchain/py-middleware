"""
Wallet Adapter for py-sdk WalletInterface

This module provides an adapter layer that wraps simple wallet implementations
(such as MockTestWallet) to conform to the complex py-sdk WalletInterface.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict

from .exceptions import BSVAuthException

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
    WalletInterface adapter for Django middleware

    Adapts simple wallet implementations (like MockTestWallet) to the
    complex py-sdk WalletInterface required by BSV middleware.

    Args:
        simple_wallet: A simple wallet implementation like MockTestWallet
    """

    def __init__(self, simple_wallet: Any) -> None:
        self.simple_wallet = simple_wallet
        logger.debug(f"WalletAdapter initialized with {type(simple_wallet).__name__}")

    # === Core methods used by middleware ===

    def get_public_key(self, args: Dict[str, Any], originator: str) -> Any:
        """
        py-sdk format: get_public_key(args, originator)
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
                    return item in ["publicKey", "public_key", "hex"]

                def __getitem__(self, key: str) -> Any:
                    # Support result['publicKey'] for test compatibility
                    key_map = {
                        "publicKey": self.publicKey,
                        "public_key": self.public_key,
                        "hex": self.hex,
                    }
                    if key in key_map:
                        return key_map[key]
                    raise KeyError(key)

            result = PublicKeyResult(pub_key_hex, pub_key_obj)
            logger.debug(
                f"get_public_key: returning object with public_key.hex()={pub_key_obj.hex()[:20]}..."
            )
            return result
        except Exception as e:
            logger.error(f"get_public_key error: {e}")
            raise

    def create_signature(self, args: Dict[str, Any], originator: str) -> Any:
        """
        py-sdk format: create_signature(args, originator)
        simple format: sign_message(message: bytes) -> bytes

        py-sdk expects specific args format for signatures
        """
        try:
            logger.debug(f"create_signature called with args: {args}")

            # py-sdk uses complex argument structures
            encryption_args = args.get("encryption_args", {})
            protocol_id = encryption_args.get("protocol_id", {})
            protocol_name = protocol_id.get("protocol_name", "")

            # Process based on signature algorithm
            signature_alg = protocol_id.get("signature_alg", "")

            # Get data from multiple possible locations
            message = args.get("data", b"")
            if not message:
                message = args.get("message", b"")
            if not message:
                # Handle case where data is directly provided as byte array
                message = encryption_args.get("data", b"")

            if isinstance(message, str):
                message = message.encode("utf-8")
            elif isinstance(message, (list, tuple)):
                # Convert byte array to bytes
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
                    return item in ["signature", "algorithm", "protocol"]

                def __getitem__(self, key: str) -> Any:
                    # Support result['signature'] for test compatibility
                    key_map = {
                        "signature": self.signature,
                        "algorithm": self.algorithm,
                        "protocol": self.protocol,
                    }
                    if key in key_map:
                        return key_map[key]
                    raise KeyError(key)

            result = SignatureResult(signature, signature_alg or "ECDSA_secp256k1", protocol_name)
            logger.debug(f"create_signature result: signature_len={len(signature)}")
            return result

        except Exception as e:
            logger.error(f"create_signature error: {e}")
            logger.error(f"create_signature args: {args}")
            import traceback

            traceback.print_exc()
            raise

    def internalize_action(self, args: Dict[str, Any], originator: str) -> Any:
        """
        py-sdk format: internalize_action(args, originator)
        simple format: internalize_action(action: dict) -> dict

        Critical method used for payment processing
        """
        try:
            # Get action data from args
            action = args.get("action", {})
            if not action:
                # If args itself is the action
                action = args

            logger.debug(f"internalize_action: action={action}")
            result = self.simple_wallet.internalize_action(action)

            # Convert to py-sdk expected format
            py_sdk_result = {
                "accepted": result.get("accepted", True),
                "satoshisPaid": result.get("satoshisPaid", 0),
                "transactionId": result.get("transactionId", "unknown"),
            }

            logger.debug(f"internalize_action result: {py_sdk_result}")
            return py_sdk_result
        except Exception as e:
            logger.error(f"internalize_action error: {e}")
            raise

    # === Other required abstract methods (basic implementations) ===

    def encrypt(self, args: Dict[str, Any], originator: str) -> Any:
        """Encryption - not implemented in simple wallet"""
        logger.warning("encrypt method called but not implemented in simple wallet")
        raise NotImplementedError("encrypt not implemented in simple wallet")

    def decrypt(self, args: Dict[str, Any], originator: str) -> Any:
        """Decryption - not implemented in simple wallet"""
        logger.warning("decrypt method called but not implemented in simple wallet")
        raise NotImplementedError("decrypt not implemented in simple wallet")

    def create_hmac(self, args: Dict[str, Any], originator: str) -> Any:
        """HMAC creation - using signature as fallback"""
        logger.warning("create_hmac called, using signature instead")
        return self.create_signature(args, originator)

    def verify_hmac(self, args: Dict[str, Any], originator: str) -> Any:
        """HMAC verification - simplified implementation"""
        logger.warning("verify_hmac called, returning True (simplified)")
        return {"valid": True}

    def verify_signature(self, args: Dict[str, Any], originator: str) -> Any:
        """Signature verification - simplified implementation"""
        logger.debug("verify_signature called")
        return {"valid": True}

    # === Wallet operation methods ===

    def create_action(self, args: Dict[str, Any], originator: str) -> Any:
        """Action creation - simplified implementation"""
        logger.debug(f"create_action: args={args}")
        return {"action": args, "status": "created", "actionId": "mock_action_id"}

    def sign_action(self, args: Dict[str, Any], originator: str) -> Any:
        """Action signing - simplified implementation"""
        logger.debug(f"sign_action: args={args}")
        return {"signed": True, "actionId": args.get("actionId", "unknown")}

    def abort_action(self, args: Dict[str, Any], originator: str) -> Any:
        """Action abort - simplified implementation"""
        logger.debug(f"abort_action: args={args}")
        return {"aborted": True}

    def list_actions(self, args: Dict[str, Any], originator: str) -> Any:
        """List actions - returns empty list"""
        return {"actions": []}

    def list_outputs(self, args: Dict[str, Any], originator: str) -> Any:
        """List outputs - returns empty list"""
        return {"outputs": []}

    def relinquish_output(self, args: Dict[str, Any], originator: str) -> Any:
        """Relinquish output - simplified implementation"""
        return {"relinquished": True}

    # === Key-related methods ===

    def reveal_counterparty_key_linkage(self, args: Dict[str, Any], originator: str) -> Any:
        """Reveal counterparty key linkage - not implemented"""
        raise NotImplementedError("reveal_counterparty_key_linkage not implemented")

    def reveal_specific_key_linkage(self, args: Dict[str, Any], originator: str) -> Any:
        """Reveal specific key linkage - not implemented"""
        raise NotImplementedError("reveal_specific_key_linkage not implemented")

    # === Certificate-related methods ===

    def acquire_certificate(self, args: Dict[str, Any], originator: str) -> Any:
        """Acquire certificate - not implemented"""
        logger.warning("acquire_certificate called but not implemented")
        return {"certificate": None}

    def list_certificates(self, args: Dict[str, Any], originator: str) -> Any:
        """List certificates - returns empty list"""
        return {"certificates": []}

    def prove_certificate(self, args: Dict[str, Any], originator: str) -> Any:
        """Prove certificate - simplified implementation"""
        return {"proof": "mock_proof"}

    def relinquish_certificate(self, args: Dict[str, Any], originator: str) -> Any:
        """Relinquish certificate - simplified implementation"""
        return {"relinquished": True}

    # === Discovery methods ===

    def discover_by_identity_key(self, args: Dict[str, Any], originator: str) -> Any:
        """Discover by identity key - simplified implementation"""
        identity_key = args.get("identityKey", "unknown")
        return {"found": False, "identityKey": identity_key}

    def discover_by_attributes(self, args: Dict[str, Any], originator: str) -> Any:
        """Discover by attributes - simplified implementation"""
        return {"found": False, "attributes": args.get("attributes", {})}

    # === Authentication methods ===

    def is_authenticated(self, args: Any, originator: str) -> Any:
        """Check authentication status - always returns True"""
        return {"authenticated": True}

    def wait_for_authentication(self, args: Any, originator: str) -> Any:
        """Wait for authentication - returns immediately as authenticated"""
        return {"authenticated": True}

    # === Network information methods ===

    def get_height(self, args: Any, originator: str) -> Any:
        """Get block height - returns mock value"""
        return {"height": 800000}

    def get_header_for_height(self, args: Dict[str, Any], originator: str) -> Any:
        """Get header for specific height - returns mock value"""
        height = args.get("height", 800000)
        return {"height": height, "header": "mock_header_data"}

    def get_network(self, args: Any, originator: str) -> Any:
        """Get network information - returns mainnet"""
        return {"network": "mainnet"}

    def get_version(self, args: Any, originator: str) -> Any:
        """Get version information"""
        return {"version": "1.0.0", "adapter": "MiddlewareWalletAdapter"}


class ProtoWalletAdapter:
    """
    Lightweight adapter for ProtoWallet to convert get_public_key response format.
    ProtoWallet returns Dict, but Peer expects object with public_key attribute.
    """

    def __init__(self, wallet_impl: Any):
        self.wallet_impl = wallet_impl
        logger.debug("Created ProtoWalletAdapter")

    def get_public_key(self, args: Dict[str, Any], originator: str) -> Any:
        """Convert ProtoWallet Dict response to object with public_key attribute."""
        result = self.wallet_impl.get_public_key(args, originator)

        if isinstance(result, dict):
            if "error" in result:
                raise Exception(result["error"])

            pub_key_hex = result.get("publicKey") or result.get("public_key")
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

    def create_signature(self, args: Dict[str, Any], originator: str) -> Any:
        """
        Convert ProtoWallet Dict response to object with signature attribute.
        Transforms nested encryption_args structure to BRC-100 compliant flat structure.

        py-sdk Peer uses:
            encryption_args.protocol_id = {securityLevel: 2, protocol: 'auth'}
            encryption_args.key_id = 'nonce1 nonce2'
            encryption_args.counterparty = {type: 3, counterparty: PublicKey}

        py-wallet-toolbox expects:
            protocolID = [securityLevel, protocol]
            keyID = 'nonce1 nonce2'
            counterparty = hex_string
        """
        logger.debug(f"[ADAPTER] create_signature called with args: {list(args.keys())}")

        # BRC-100 compliant: Convert nested encryption_args to flat structure
        enc_args = args.get("encryption_args", {})
        if enc_args:
            logger.debug(f"[ADAPTER] Found encryption_args: {list(enc_args.keys())}")

            # Extract protocol_id and convert to protocolID format [securityLevel, protocol]
            protocol_id = enc_args.get("protocol_id", {})
            if isinstance(protocol_id, dict):
                security_level = protocol_id.get("securityLevel", 2)
                protocol = protocol_id.get("protocol", "auth")
                protocol_id_list = [security_level, protocol]
            else:
                protocol_id_list = protocol_id

            # Extract counterparty - py-sdk sends {type: 3, counterparty: PublicKey}
            counterparty_arg = enc_args.get("counterparty")
            counterparty_hex = None
            if isinstance(counterparty_arg, dict):
                cp_value = counterparty_arg.get("counterparty")
                if cp_value:
                    # Convert PublicKey to hex string
                    if hasattr(cp_value, "hex"):
                        counterparty_hex = cp_value.hex()
                    elif isinstance(cp_value, str):
                        counterparty_hex = cp_value
            elif counterparty_arg:
                if hasattr(counterparty_arg, "hex"):
                    counterparty_hex = counterparty_arg.hex()
                else:
                    counterparty_hex = str(counterparty_arg)

            # Build flat args for py-wallet-toolbox
            flat_args = {
                "protocolID": protocol_id_list,
                "keyID": enc_args.get("key_id", "1"),
                "counterparty": counterparty_hex,
                "data": args.get("data"),
            }

            # Add optional fields
            if args.get("hash_to_directly_sign"):
                flat_args["hashToDirectlySign"] = args.get("hash_to_directly_sign")

            logger.debug(
                f"[ADAPTER] Converted to flat_args: protocolID={flat_args.get('protocolID')}, keyID={flat_args.get('keyID')}, counterparty={flat_args.get('counterparty', '')[:20] if flat_args.get('counterparty') else None}..."
            )

            args = flat_args

        result = self.wallet_impl.create_signature(args, originator)

        if isinstance(result, dict):
            if "error" in result:
                logger.error(f"create_signature error: {result['error']}")
                raise Exception(result["error"])

            signature = result.get("signature")
            if signature:

                class SignatureResult:
                    def __init__(self, sig: bytes):
                        self.signature = sig

                return SignatureResult(signature)

        return result

    def verify_signature(self, args: Dict[str, Any], originator: str) -> Any:
        """
        Normalize verify_signature arguments to BRC-100 compliant flat structure.
        Handles BOTH nested encryption_args format AND flat py-sdk format.
        """
        logger.debug(f"[ADAPTER] verify_signature called! originator={originator}")

        # Check if args are in nested encryption_args format or flat py-sdk format
        enc_args = args.get("encryption_args", {})
        if enc_args:
            # Legacy nested format with encryption_args
            # Extract protocol_id - may be nested object or flat
            protocol_id = enc_args.get("protocol_id")
            if isinstance(protocol_id, dict):
                # Convert nested protocol_id to BRC-100 format
                protocol_id_val = [
                    protocol_id.get("securityLevel", 2),
                    protocol_id.get("protocol", ""),
                ]
            else:
                protocol_id_val = protocol_id

            # Normalize signature to bytes
            signature = args.get("signature")
            if signature is not None:
                if isinstance(signature, (list, tuple)):
                    signature = bytes(signature)
                elif isinstance(signature, str):
                    try:
                        signature = bytes.fromhex(signature)
                    except ValueError:
                        pass  # Keep as-is if not valid hex

            # Normalize data to bytes
            data = args.get("data")
            if data is not None:
                if isinstance(data, (list, tuple)):
                    data = bytes(data)

            # Flatten the structure for BRC-100 compliance (camelCase for ToolboxWallet)
            flat_args = {
                "protocolID": protocol_id_val,  # camelCase for ToolboxWallet
                "keyID": enc_args.get("key_id"),  # camelCase for ToolboxWallet
                "counterparty": enc_args.get("counterparty"),
                "forSelf": enc_args.get("for_self", False),  # camelCase for ToolboxWallet
                "data": data,
                "signature": signature,
            }
            # Only include hashToDirectlyVerify if it's not None
            hash_to_verify = args.get("hash_to_directly_verify")
            if hash_to_verify is not None:
                flat_args["hashToDirectlyVerify"] = hash_to_verify

            # Normalize counterparty to hex string (ToolboxWallet expects string)
            try:
                cp = flat_args.get("counterparty")
                if isinstance(cp, dict):
                    # Extract counterparty from nested dict
                    inner_cp = cp.get("counterparty")
                    if inner_cp is not None:
                        # Convert PublicKey object to hex string
                        if hasattr(inner_cp, "hex") and callable(inner_cp.hex):
                            flat_args["counterparty"] = inner_cp.hex()
                        elif hasattr(inner_cp, "__str__"):
                            cp_str = str(inner_cp)
                            # Extract hex from string like "<PublicKey hex=...>"
                            if "hex=" in cp_str:
                                flat_args["counterparty"] = cp_str.split("hex=")[1].rstrip(">")
                            else:
                                flat_args["counterparty"] = cp_str
                        else:
                            flat_args["counterparty"] = str(inner_cp)
                    else:
                        flat_args["counterparty"] = None
                elif cp is not None:
                    # Convert PublicKey object to hex string
                    if hasattr(cp, "hex") and callable(cp.hex):
                        flat_args["counterparty"] = cp.hex()
                    elif isinstance(cp, str):
                        flat_args["counterparty"] = cp
                    else:
                        flat_args["counterparty"] = str(cp)
            except Exception as e:
                logger.debug(f"verify_signature counterparty conversion failed: {e}")
            args = flat_args
        else:
            # Flat py-sdk format - convert in place

            # Convert protocolID from dict to list
            protocol_id = args.get("protocolID")
            if isinstance(protocol_id, dict):
                args["protocolID"] = [
                    protocol_id.get("securityLevel", 2),
                    protocol_id.get("protocol", ""),
                ]

            # Convert counterparty from dict to hex string
            counterparty = args.get("counterparty")
            if isinstance(counterparty, dict):
                inner_cp = counterparty.get("counterparty")
                if inner_cp is not None:
                    if hasattr(inner_cp, "hex") and callable(inner_cp.hex):
                        args["counterparty"] = inner_cp.hex()
                    elif hasattr(inner_cp, "__str__"):
                        cp_str = str(inner_cp)
                        if "hex=" in cp_str:
                            args["counterparty"] = cp_str.split("hex=")[1].rstrip(">")
                        else:
                            args["counterparty"] = cp_str
                    else:
                        args["counterparty"] = str(inner_cp)

            # Ensure signature is bytes
            signature = args.get("signature")
            if signature is not None and isinstance(signature, (list, tuple)):
                args["signature"] = bytes(signature)

            # Ensure data is bytes
            data = args.get("data")
            if data is not None and isinstance(data, (list, tuple)):
                args["data"] = bytes(data)

        # Call underlying verify_signature and wrap result as object
        result = self.wallet_impl.verify_signature(args, originator)
        logger.debug(f"[ADAPTER] verify_signature result: {result}")

        if isinstance(result, dict):
            # Convert dict to object with .valid attribute (Peer expects object)
            class VerifyResult:
                def __init__(self, valid: bool, error: str = None):
                    self.valid = valid
                    self.error = error

            if "error" in result:
                logger.debug(f"[ADAPTER] verify_signature error: {result['error']}")
                return VerifyResult(False, result["error"])

            valid = result.get("valid", False)
            logger.debug(f"[ADAPTER] signature verification: {valid}")
            return VerifyResult(valid)

        return result

    def create_hmac(self, args: Dict[str, Any], originator: str) -> Any:
        """
        Delegate create_hmac to underlying wallet_impl (ProtoWallet).

        Since py-sdk's create_nonce() now matches TypeScript exactly with flat structure,
        we can pass args directly without conversion.
        """
        logger.debug(
            "[ProtoWalletAdapter] create_hmac called with flat args (no conversion needed)"
        )
        result = self.wallet_impl.create_hmac(args, originator)

        if isinstance(result, dict):
            if "error" in result:
                logger.error(f"create_hmac error: {result['error']}")
                raise Exception(result["error"])

            class HmacResult:
                def __init__(self, hmac: bytes):
                    self.hmac = hmac

            hmac_bytes = result.get("hmac")
            if hmac_bytes:
                return HmacResult(hmac_bytes)

        return result

    def verify_hmac(self, args: Dict[str, Any], originator: str) -> Any:
        """
        Delegate verify_hmac to underlying wallet_impl (ProtoWallet).

        Since py-sdk's verify_nonce() now matches TypeScript exactly with flat structure,
        we can pass args directly without conversion.
        """
        logger.debug(
            "[ProtoWalletAdapter] verify_hmac called with flat args (no conversion needed)"
        )
        result = self.wallet_impl.verify_hmac(args, originator)

        if isinstance(result, dict):

            class VerifyHmacResult:
                def __init__(self, valid: bool):
                    self.valid = valid

            valid = result.get("valid", False)
            return VerifyHmacResult(valid)

        return result

    def __getattr__(self, name: str) -> Any:
        """Delegate all other methods to the wrapped ProtoWallet."""
        return getattr(self.wallet_impl, name)


def create_wallet_adapter(simple_wallet: Any) -> Any:
    """
    Create py-sdk compatible wallet adapter from simple wallet

    Args:
        simple_wallet: A simple wallet implementation like MockTestWallet, or ProtoWallet

    Returns:
        An adapter compatible with py-sdk WalletInterface
    """
    if not PY_SDK_AVAILABLE:
        logger.error(
            "py-sdk is required but not available; refusing to bypass with a simple wrapper"
        )
        raise BSVAuthException(
            message="py-sdk is required for wallet adapter but not available",
            details={
                "module": "wallet_adapter",
                "hint": "Install py-sdk and ensure it is importable",
            },
        )

    # Check if wallet is already a full ProtoWallet (has create_action, internalize_action, etc.)
    if hasattr(simple_wallet, "create_action") and hasattr(simple_wallet, "internalize_action"):
        logger.debug("Wallet is ProtoWallet, wrapping with ProtoWalletAdapter")
        return ProtoWalletAdapter(simple_wallet)

    # Otherwise, wrap it with full adapter
    return MiddlewareWalletAdapter(simple_wallet)
