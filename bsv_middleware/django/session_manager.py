"""
Django Session Manager for BSV Middleware

This module provides Django-specific session management for BSV authentication,
integrating with Django's session framework.
"""

import logging
from typing import Optional, Dict, Any
from django.contrib.sessions.backends.base import SessionBase

from ..types import SessionManagerInterface, PubKeyHex

logger = logging.getLogger(__name__)


class DjangoSessionManager:
    """
    Django-specific session manager for BSV authentication.
    
    This class integrates with Django's session framework to manage
    BSV authentication state, equivalent to Express SessionManager.
    """
    
    def __init__(self, session: SessionBase):
        """
        Initialize the session manager with a Django session.
        
        Args:
            session: Django session object from request.session
        """
        self.session = session
        self._bsv_session_prefix = 'bsv_auth_'
    
    def has_session(self, identity_key: PubKeyHex) -> bool:
        """
        Check if a BSV session exists for the given identity key.
        
        Equivalent to Express: sessionManager.hasSession(identityKey)
        
        Args:
            identity_key: The BSV identity key to check
            
        Returns:
            True if a session exists, False otherwise
        """
        try:
            session_key = f"{self._bsv_session_prefix}{identity_key}"
            return session_key in self.session
        except Exception as e:
            logger.error(f"Failed to check session for {identity_key}: {e}")
            return False
    
    def create_session(
        self,
        identity_key: PubKeyHex,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Create a new BSV session for the given identity key.
        
        Args:
            identity_key: The BSV identity key
            auth_data: Optional additional authentication data
        """
        try:
            session_key = f"{self._bsv_session_prefix}{identity_key}"
            session_data = {
                'identity_key': identity_key,
                'created_at': self._get_current_timestamp(),
                'auth_data': auth_data or {}
            }
            
            self.session[session_key] = session_data
            self.session.save()
            
            logger.debug(f"Created BSV session for {identity_key}")
            
        except Exception as e:
            logger.error(f"Failed to create session for {identity_key}: {e}")
            raise
    
    def get_session(self, identity_key: PubKeyHex) -> Optional[Dict[str, Any]]:
        """
        Get the BSV session data for the given identity key.
        
        Args:
            identity_key: The BSV identity key
            
        Returns:
            Session data if exists, None otherwise
        """
        try:
            session_key = f"{self._bsv_session_prefix}{identity_key}"
            return self.session.get(session_key)
        except Exception as e:
            logger.error(f"Failed to get session for {identity_key}: {e}")
            return None
    
    def update_session(
        self,
        identity_key: PubKeyHex,
        auth_data: Dict[str, Any]
    ) -> None:
        """
        Update the BSV session data for the given identity key.
        
        Args:
            identity_key: The BSV identity key
            auth_data: Updated authentication data
        """
        try:
            session_key = f"{self._bsv_session_prefix}{identity_key}"
            
            if session_key in self.session:
                session_data = self.session[session_key]
                session_data['auth_data'].update(auth_data)
                session_data['updated_at'] = self._get_current_timestamp()
                
                self.session[session_key] = session_data
                self.session.save()
                
                logger.debug(f"Updated BSV session for {identity_key}")
            else:
                logger.warning(f"Attempted to update non-existent session for {identity_key}")
                
        except Exception as e:
            logger.error(f"Failed to update session for {identity_key}: {e}")
            raise
    
    def delete_session(self, identity_key: PubKeyHex) -> None:
        """
        Delete the BSV session for the given identity key.
        
        Args:
            identity_key: The BSV identity key
        """
        try:
            session_key = f"{self._bsv_session_prefix}{identity_key}"
            
            if session_key in self.session:
                del self.session[session_key]
                self.session.save()
                logger.debug(f"Deleted BSV session for {identity_key}")
            else:
                logger.debug(f"No session to delete for {identity_key}")
                
        except Exception as e:
            logger.error(f"Failed to delete session for {identity_key}: {e}")
            raise
    
    def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up expired BSV sessions.
        
        Args:
            max_age_seconds: Maximum age of sessions in seconds (default: 1 hour)
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            current_time = self._get_current_timestamp()
            expired_sessions = []
            
            for key in list(self.session.keys()):
                if key.startswith(self._bsv_session_prefix):
                    session_data = self.session.get(key, {})
                    created_at = session_data.get('created_at', 0)
                    
                    if current_time - created_at > max_age_seconds:
                        expired_sessions.append(key)
            
            for session_key in expired_sessions:
                del self.session[session_key]
            
            if expired_sessions:
                self.session.save()
                logger.info(f"Cleaned up {len(expired_sessions)} expired BSV sessions")
            
            return len(expired_sessions)
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp for session tracking."""
        import time
        return time.time()


# Factory function for easy instantiation
def create_django_session_manager(session) -> DjangoSessionManager:
    """
    Create a Django session manager instance.
    
    Equivalent to Express: new SessionManager()
    """
    return DjangoSessionManager(session)
