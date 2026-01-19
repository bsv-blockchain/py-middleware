"""
Django Session Manager for BSV Middleware

This module provides Django-specific session management for BSV authentication,
integrating with Django's session framework.
"""

import logging
from typing import Any, Dict, Optional

from django.contrib.sessions.backends.base import SessionBase

from bsv_middleware.types import PubKeyHex

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
        self._bsv_session_prefix = "bsv_auth_"

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
        self, identity_key: PubKeyHex, auth_data: Optional[Dict[str, Any]] = None
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
                "identity_key": identity_key,
                "created_at": self._get_current_timestamp(),
                "auth_data": auth_data or {},
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
            result: Optional[Dict[str, Any]] = self.session.get(session_key)
            return result
        except Exception as e:
            logger.error(f"Failed to get session for {identity_key}: {e}")
            return None

    def update_session(self, identity_key: PubKeyHex, auth_data: Dict[str, Any]) -> None:
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
                session_data["auth_data"].update(auth_data)
                session_data["updated_at"] = self._get_current_timestamp()

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
                    created_at = session_data.get("created_at", 0)

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


class DjangoSessionManagerAdapter:
    """
    Adapter to make DjangoSessionManager compatible with py-sdk SessionManager interface.

    py-sdk Peer expects:
    - add_session(session: PeerSession) -> None
    - get_session(identifier: str) -> Optional[PeerSession]
    """

    def __init__(self, django_session_manager: DjangoSessionManager):
        self.django_sm = django_session_manager

    def add_session(self, session: Any) -> None:
        """
        Add a PeerSession to Django session storage.

        NOTE: This adapter is for optional persistence to Django HTTP sessions.
        The primary session management uses DefaultSessionManager (in-memory),
        which correctly handles multiple concurrent sessions per identity key.

        Args:
            session: PeerSession object from py-sdk
        """
        try:
            # Extract identity key from session
            if hasattr(session, "peer_identity_key") and session.peer_identity_key:
                identity_key = (
                    session.peer_identity_key.hex()
                    if hasattr(session.peer_identity_key, "hex")
                    else str(session.peer_identity_key)
                )
            else:
                logger.warning("PeerSession without peer_identity_key, cannot save")
                return

            # Serialize PeerSession to dict
            session_data = {
                "is_authenticated": getattr(session, "is_authenticated", False),
                "session_nonce": getattr(session, "session_nonce", ""),
                "peer_nonce": getattr(session, "peer_nonce", ""),
                "peer_identity_key": identity_key,
                "last_update": getattr(session, "last_update", 0),
            }

            self.django_sm.create_session(identity_key, session_data)
            logger.debug(f"Saved PeerSession for {identity_key[:20]}...")

        except Exception as e:
            logger.error(f"Failed to add session: {e}")
            import traceback

            traceback.print_exc()

    def get_session(self, identifier: str) -> Optional[Any]:
        """
        Get a PeerSession from Django session storage.

        NOTE: This adapter is for optional persistence only.
        Primary lookups use DefaultSessionManager which supports
        lookups by both session_nonce and identity_key.

        Args:
            identifier: Identity key (public key hex)

        Returns:
            PeerSession object or None
        """
        try:
            session_data = self.django_sm.get_session(identifier)

            if not session_data or "auth_data" not in session_data:
                return None

            auth_data = session_data["auth_data"]

            # Deserialize dict to PeerSession
            try:
                from bsv.auth.peer_session import PeerSession
                from bsv.keys import PublicKey
            except ImportError:
                logger.error("Cannot import PeerSession from py-sdk")
                return None

            # Reconstruct PeerSession
            peer_identity_key = None
            if "peer_identity_key" in auth_data:
                try:
                    peer_identity_key = PublicKey(auth_data["peer_identity_key"])
                except Exception as e:
                    logger.warning(f"Failed to parse peer_identity_key: {e}")

            peer_session = PeerSession(
                is_authenticated=auth_data.get("is_authenticated", False),
                session_nonce=auth_data.get("session_nonce", ""),
                peer_nonce=auth_data.get("peer_nonce", ""),
                peer_identity_key=peer_identity_key,
                last_update=auth_data.get("last_update", 0),
            )

            return peer_session

        except Exception as e:
            logger.error(f"Failed to get session for {identifier}: {e}")
            import traceback

            traceback.print_exc()
            return None

    def has_session(self, identifier: str) -> bool:
        """Check if session exists."""
        return self.django_sm.has_session(identifier)

    def update_session(self, session: Any) -> None:
        """
        Update an existing PeerSession.

        Args:
            session: Updated PeerSession object
        """
        # Simply call add_session, which will overwrite
        self.add_session(session)


# Factory function for easy instantiation
def create_django_session_manager(session: Any) -> DjangoSessionManager:
    """
    Create a Django session manager instance.

    Equivalent to Express: new SessionManager()
    """
    return DjangoSessionManager(session)
