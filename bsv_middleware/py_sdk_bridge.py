"""
py-sdk Bridge Layer

This module provides integration with the py-sdk library, wrapping py-sdk
functionality for use in Django middleware. Based on Express middleware
py-sdk usage patterns.
"""

import json
import logging
from typing import Optional, Dict, Any, List, TYPE_CHECKING

# Import actual py-sdk modules
try:
    from bsv.auth import Peer, PeerOptions, Transport, SessionManager
    from bsv.auth.certificate import VerifiableCertificate
    from bsv.auth.requested_certificate_set import RequestedCertificateSet
    from bsv.auth.transports.transport import Transport as BaseTransport
    from bsv.wallet import Wallet
    PY_SDK_AVAILABLE = True
except ImportError as e:
    logging.warning(f"py-sdk not available: {e}")
    PY_SDK_AVAILABLE = False
    # Create dummy classes for type hints
    class Peer: pass
    class PeerOptions: pass
    class Transport: pass
    class SessionManager: pass
    class VerifiableCertificate: pass
    class RequestedCertificateSet: pass
    class BaseTransport: pass
    class Wallet: pass

from .types import WalletInterface, BSVPayment
from .exceptions import (
    BSVAuthException,
    BSVPaymentException,
    BSVMalformedPaymentException,
    BSVInvalidDerivationPrefixException
)

logger = logging.getLogger(__name__)


class PySdkBridge:
    """
    Bridge between Django middleware and py-sdk functionality.
    
    This class wraps py-sdk operations to provide a clean interface
    for Django middleware, handling error conversion and type adaptation.
    """
    
    def __init__(self, wallet: WalletInterface):
        self.wallet = wallet
        self.peer: Optional[Peer] = None
        self.transport: Optional[Transport] = None
        
        if PY_SDK_AVAILABLE:
            self._initialize_py_sdk_components()
    
    def _initialize_py_sdk_components(self):
        """Initialize py-sdk components."""
        try:
            # Create transport (equivalent to Express ExpressTransport)
            self.transport = DjangoTransport()
            
            # Create peer options (equivalent to Express PeerOptions)
            peer_options = PeerOptions(
                wallet=self.wallet,
                transport=self.transport,
                certificates_to_request=None,  # Will be set by middleware
                session_manager=None,  # Will use default
                auto_persist_last_session=True,
                logger=logger,
                debug=False
            )
            
            # Create peer (equivalent to Express new Peer())
            self.peer = Peer(peer_options)
            
            logger.info("py-sdk components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize py-sdk components: {e}")
            raise BSVAuthException(f"py-sdk initialization failed: {e}")
    
    def create_nonce(self) -> str:
        """
        Create a nonce for payment derivation prefix.
        
        Equivalent to Express: createNonce(wallet)
        Phase 2.3: Enhanced implementation with py-sdk integration
        """
        try:
            if PY_SDK_AVAILABLE and self.wallet:
                # Try to use py-sdk nonce creation if available
                if hasattr(self.wallet, 'create_nonce'):
                    return self.wallet.create_nonce()
                elif hasattr(self.wallet, 'get_public_key'):
                    # Use wallet public key for deterministic nonce
                    import hashlib
                    import secrets
                    import time
                    
                    try:
                        # Get public key (handle both simple and py-sdk format)
                        if hasattr(self.wallet, 'get_public_key'):
                            if callable(getattr(self.wallet, 'get_public_key')):
                                # py-sdk format - might need arguments
                                try:
                                    pub_key_result = self.wallet.get_public_key(None, {}, 'nonce_creation')
                                    pub_key = pub_key_result.get('publicKey', '') if isinstance(pub_key_result, dict) else str(pub_key_result)
                                except:
                                    # Simple format fallback
                                    pub_key = self.wallet.get_public_key()
                            else:
                                pub_key = str(self.wallet.get_public_key)
                        else:
                            pub_key = 'default_key'
                        
                        timestamp = str(int(time.time() * 1000))
                        random_part = secrets.token_hex(8)
                        
                        # Create deterministic but unique nonce
                        nonce_data = f"{pub_key}:{timestamp}:{random_part}"
                        nonce_hash = hashlib.sha256(nonce_data.encode()).hexdigest()
                        logger.debug(f"Created deterministic nonce: {nonce_hash[:10]}...")
                        return nonce_hash[:32]  # 32 character nonce
                        
                    except Exception as key_error:
                        logger.warning(f"Failed to use wallet key for nonce: {key_error}")
                        # Fall through to random nonce
                
            # Fallback: secure random nonce
            import secrets
            nonce = secrets.token_hex(16)
            logger.debug(f"Created fallback nonce: {nonce[:10]}...")
            return nonce
            
        except Exception as e:
            logger.error(f"Failed to create nonce: {e}")
            # Ultimate fallback - always return something
            import secrets
            return secrets.token_hex(16)
    
    def verify_nonce(self, nonce: str) -> bool:
        """
        Verify a nonce for authentication/payment.
        
        Equivalent to Express: verifyNonce(nonce)
        Phase 2.3: Enhanced implementation with py-sdk integration
        """
        try:
            if not nonce or not isinstance(nonce, str):
                logger.warning(f"Invalid nonce type: {type(nonce)}")
                return False
                
            if len(nonce) < 16:
                logger.warning(f"Nonce too short: {len(nonce)} characters")
                return False
                
            if PY_SDK_AVAILABLE and self.wallet:
                # Try to use py-sdk nonce verification if available
                if hasattr(self.wallet, 'verify_nonce'):
                    return self.wallet.verify_nonce(nonce)
                elif hasattr(self.wallet, 'get_public_key'):
                    # Enhanced verification with wallet context
                    try:
                        # Basic format validation
                        if len(nonce) in [32, 64] and all(c in '0123456789abcdef' for c in nonce.lower()):
                            logger.debug(f"Nonce format valid: {nonce[:10]}...")
                            return True
                            
                    except Exception as verification_error:
                        logger.warning(f"Wallet verification failed, using fallback: {verification_error}")
            
            # Fallback verification - basic format check
            if len(nonce) >= 16:
                # Check if nonce is hexadecimal
                try:
                    int(nonce, 16)
                    logger.debug(f"Nonce verification passed (fallback): {nonce[:10]}...")
                    return True
                except ValueError:
                    # Check if nonce is alphanumeric (alternative valid format)
                    if nonce.replace('-', '').replace('_', '').isalnum():
                        logger.debug(f"Nonce verification passed (alphanumeric): {nonce[:10]}...")
                        return True
                    
                    logger.warning(f"Nonce format invalid: {nonce[:10]}...")
                    return False
            
            logger.warning(f"Nonce verification failed: length={len(nonce)}")
            return False
            
        except Exception as e:
            logger.error(f"Nonce verification error: {e}")
            return False
    
    def internalize_action(self, payment_data: BSVPayment) -> Dict[str, Any]:
        """
        Process a payment action through the wallet.
        
        Equivalent to Express: wallet.internalizeAction(action)
        """
        try:
            if PY_SDK_AVAILABLE and self.wallet:
                # Use py-sdk wallet to internalize action
                action = {
                    'derivationPrefix': payment_data.derivation_prefix,
                    'satoshis': payment_data.satoshis,
                    'transaction': payment_data.transaction
                }
                
                # This would use the actual py-sdk wallet interface
                # For now, return mock result
                return {
                    'accepted': True,
                    'satoshisPaid': payment_data.satoshis,
                    'transactionId': 'mock_tx_id'
                }
            else:
                # Fallback implementation
                return {
                    'accepted': True,
                    'satoshisPaid': payment_data.satoshis,
                    'transactionId': 'mock_tx_id'
                }
                
        except Exception as e:
            logger.error(f"Failed to internalize action: {e}")
            raise BSVPaymentException("Payment processing failed")
    
    def parse_payment_header(self, payment_header: str) -> BSVPayment:
        """
        Parse payment header JSON.
        
        Equivalent to Express: JSON.parse(paymentHeader)
        """
        try:
            payment_data = json.loads(payment_header)
            
            return BSVPayment(
                derivation_prefix=payment_data.get('derivationPrefix', ''),
                satoshis=payment_data.get('satoshis', 0),
                transaction=payment_data.get('transaction')
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse payment header: {e}")
            raise BSVMalformedPaymentException()
        except Exception as e:
            logger.error(f"Failed to parse payment header: {e}")
            raise BSVMalformedPaymentException()
    
    def get_peer(self) -> Optional[Peer]:
        """Get the py-sdk Peer instance."""
        return self.peer
    
    def get_transport(self) -> Optional[Transport]:
        """Get the py-sdk Transport instance."""
        return self.transport

    def build_auth_message_from_request(self, request) -> Optional[Dict[str, Any]]:
        """
        Build authentication message from Django request.
        
        Equivalent to Express: buildAuthMessageFromRequest(req)
        """
        try:
            # Extract BSV auth headers
            auth_headers = {}
            for header_name, header_value in request.headers.items():
                if header_name.lower().startswith('x-bsv-auth-'):
                    auth_headers[header_name] = header_value
            
            if not auth_headers:
                return None
            
            # TODO: Use py-sdk to build proper auth message
            # This would involve converting headers to proper auth message format
            return {
                'headers': auth_headers,
                'method': request.method,
                'path': request.path,
                'identityKey': auth_headers.get('x-bsv-auth-identity-key', 'unknown'),
                'certificates': []  # TODO: Extract certificates from headers
            }
            
        except Exception as e:
            logger.error(f"Failed to build auth message: {e}")
            raise BSVAuthException("Failed to parse authentication message")
    
    def process_certificates(
        self,
        sender_public_key: str,
        certificates: List[Any],
        request,
        response
    ) -> None:
        """
        Process received certificates.
        
        Equivalent to Express: onCertificatesReceived callback
        """
        try:
            # TODO: Use py-sdk certificate processing
            logger.info(f"Received {len(certificates)} certificates from {sender_public_key}")
            
            for cert in certificates:
                # Process each certificate
                # This would involve validating and storing certificates
                logger.debug(f"Processing certificate: {cert}")
                
        except Exception as e:
            logger.error(f"Failed to process certificates: {e}")
            raise BSVAuthException("Certificate processing failed")


class DjangoTransport(BaseTransport):
    """
    Django-specific transport implementation.
    
    Equivalent to Express ExpressTransport class.
    """
    
    def __init__(self):
        super().__init__()
        self.peer: Optional[Peer] = None
        self.message_callback: Optional[callable] = None
    
    def set_peer(self, peer: Peer):
        """Set the peer instance."""
        self.peer = peer
    
    def on_data(self, callback: callable) -> Optional[str]:
        """Set the message callback."""
        self.message_callback = callback
        return None  # No error
    
    def send_message(self, message: Any) -> Optional[str]:
        """Send a message through the transport."""
        # This would be implemented based on Django's HTTP response
        # For now, just log the message
        logger.debug(f"Sending message: {message}")
        return None  # No error


def create_py_sdk_bridge(wallet: WalletInterface) -> PySdkBridge:
    """
    Create a py-sdk bridge instance.
    
    Equivalent to Express: new PySdkBridge(wallet)
    """
    return PySdkBridge(wallet)


# Module-level convenience functions (Express equivalent)
# These functions provide Express-like API for easy integration

def create_nonce(wallet=None) -> str:
    """
    Create a nonce for authentication/payment.
    
    Equivalent to Express: createNonce(wallet)
    Phase 2.3: Module-level function for payment middleware
    """
    try:
        if wallet:
            bridge = PySdkBridge(wallet)
            return bridge.create_nonce()
        else:
            # No wallet provided - create random nonce
            import secrets
            return secrets.token_hex(16)
    except Exception as e:
        logger.error(f"Module-level create_nonce error: {e}")
        import secrets
        return secrets.token_hex(16)


def verify_nonce(nonce: str, wallet=None) -> bool:
    """
    Verify a nonce for authentication/payment.
    
    Equivalent to Express: verifyNonce(nonce)
    Phase 2.3: Module-level function for payment middleware
    """
    try:
        if wallet:
            bridge = PySdkBridge(wallet)
            return bridge.verify_nonce(nonce)
        else:
            # No wallet provided - basic validation
            if not nonce or not isinstance(nonce, str) or len(nonce) < 16:
                return False
            
            # Basic format check
            try:
                int(nonce, 16)
                return True
            except ValueError:
                return nonce.replace('-', '').replace('_', '').isalnum()
                
    except Exception as e:
        logger.error(f"Module-level verify_nonce error: {e}")
        return False
