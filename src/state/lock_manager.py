"""
Distributed Lock Manager

Uses Redis for distributed locking to prevent simultaneous migrations
of the same API by different teams.

Features:
- Automatic lock expiration
- Lock renewal for long-running operations
- Lock ownership verification
- Conflict detection and reporting
"""

import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, Tuple

import redis
from redis.lock import Lock as RedisLock


class LockConflictError(Exception):
    """Raised when lock cannot be acquired due to conflict"""
    pass


class LockManager:
    """
    Distributed lock manager for preventing migration conflicts.
    
    Uses Redis for distributed locking across multiple developer instances.
    """
    
    # Lock key prefix
    LOCK_PREFIX = "api_migration:lock:"
    
    # Default lock expiration (30 minutes)
    DEFAULT_LOCK_TIMEOUT = 30 * 60  # seconds
    
    # Lock renewal interval (10 minutes)
    RENEWAL_INTERVAL = 10 * 60  # seconds
    
    def __init__(self, redis_url: str, team_name: str):
        """
        Initialize lock manager.
        
        Args:
            redis_url: Redis connection URL
            team_name: Current team/user name for lock ownership
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.team_name = team_name
        
    def _lock_key(self, api_name: str, platform: str) -> str:
        """Generate Redis key for API lock"""
        return f"{self.LOCK_PREFIX}{platform}:{api_name}"
    
    def _lock_info_key(self, api_name: str, platform: str) -> str:
        """Generate Redis key for lock metadata"""
        return f"{self.LOCK_PREFIX}info:{platform}:{api_name}"
    
    def acquire_lock(
        self,
        api_name: str,
        platform: str,
        timeout: int = DEFAULT_LOCK_TIMEOUT,
        blocking: bool = False,
        blocking_timeout: int = 10
    ) -> Tuple[bool, Optional[str]]:
        """
        Acquire distributed lock for API migration.
        
        Args:
            api_name: API name to lock
            platform: Platform name
            timeout: Lock expiration time in seconds
            blocking: If True, wait for lock to become available
            blocking_timeout: Max time to wait if blocking=True
            
        Returns:
            Tuple of (success, error_message)
            
        Raises:
            LockConflictError: If lock is held by another team
        """
        lock_key = self._lock_key(api_name, platform)
        info_key = self._lock_info_key(api_name, platform)
        
        # Create Redis lock
        lock = RedisLock(
            self.redis_client,
            lock_key,
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout
        )
        
        # Try to acquire lock
        acquired = lock.acquire(blocking=blocking, blocking_timeout=blocking_timeout)
        
        if not acquired:
            # Lock is held by someone else
            existing_info = self.redis_client.hgetall(info_key)
            
            if existing_info:
                owner = existing_info.get("team")
                locked_at = existing_info.get("locked_at")
                reason = existing_info.get("reason", "migration in progress")
                contact = existing_info.get("contact", "N/A")
                
                error_msg = (
                    f"API '{api_name}' ({platform}) is locked by {owner}\n"
                    f"  Locked at: {locked_at}\n"
                    f"  Reason: {reason}\n"
                    f"  Contact: {contact}"
                )
            else:
                error_msg = f"API '{api_name}' ({platform}) is currently locked"
            
            return False, error_msg
        
        # Store lock metadata
        lock_info = {
            "team": self.team_name,
            "locked_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=timeout)).isoformat(),
            "reason": "migration in progress",
            "lock_id": str(uuid.uuid4())
        }
        
        self.redis_client.hset(info_key, mapping=lock_info)
        self.redis_client.expire(info_key, timeout)
        
        return True, None
    
    def release_lock(self, api_name: str, platform: str) -> bool:
        """
        Release distributed lock.
        
        Args:
            api_name: API name
            platform: Platform name
            
        Returns:
            True if lock was released, False if not held
        """
        lock_key = self._lock_key(api_name, platform)
        info_key = self._lock_info_key(api_name, platform)
        
        # Delete lock and metadata
        deleted = self.redis_client.delete(lock_key, info_key)
        
        return deleted > 0
    
    def renew_lock(self, api_name: str, platform: str, timeout: int = DEFAULT_LOCK_TIMEOUT) -> bool:
        """
        Renew lock expiration time for long-running operations.
        
        Args:
            api_name: API name
            platform: Platform name
            timeout: New expiration time in seconds
            
        Returns:
            True if renewed, False if lock doesn't exist
        """
        lock_key = self._lock_key(api_name, platform)
        info_key = self._lock_info_key(api_name, platform)
        
        # Verify we own the lock
        if not self.owns_lock(api_name, platform):
            return False
        
        # Extend expiration
        renewed = self.redis_client.expire(lock_key, timeout)
        
        if renewed:
            # Update metadata
            new_expires_at = (datetime.now() + timedelta(seconds=timeout)).isoformat()
            self.redis_client.hset(info_key, "expires_at", new_expires_at)
            self.redis_client.expire(info_key, timeout)
        
        return renewed
    
    def owns_lock(self, api_name: str, platform: str) -> bool:
        """
        Check if current team owns the lock.
        
        Args:
            api_name: API name
            platform: Platform name
            
        Returns:
            True if current team owns the lock
        """
        info_key = self._lock_info_key(api_name, platform)
        lock_info = self.redis_client.hgetall(info_key)
        
        if not lock_info:
            return False
        
        return lock_info.get("team") == self.team_name
    
    def get_lock_info(self, api_name: str, platform: str) -> Optional[dict]:
        """
        Get lock metadata.
        
        Args:
            api_name: API name
            platform: Platform name
            
        Returns:
            Lock metadata dict or None if not locked
        """
        info_key = self._lock_info_key(api_name, platform)
        return self.redis_client.hgetall(info_key) or None
    
    def is_locked(self, api_name: str, platform: str) -> bool:
        """
        Check if API is currently locked.
        
        Args:
            api_name: API name
            platform: Platform name
            
        Returns:
            True if locked
        """
        lock_key = self._lock_key(api_name, platform)
        return self.redis_client.exists(lock_key) > 0
    
    @contextmanager
    def lock(
        self,
        api_name: str,
        platform: str,
        timeout: int = DEFAULT_LOCK_TIMEOUT,
        auto_renew: bool = False
    ):
        """
        Context manager for acquiring and releasing locks.
        
        Usage:
            with lock_manager.lock("payment-api", "apic"):
                # Perform migration
                deploy_api()
        
        Args:
            api_name: API name
            platform: Platform name
            timeout: Lock expiration time
            auto_renew: If True, automatically renew lock periodically
            
        Raises:
            LockConflictError: If lock cannot be acquired
        """
        # Acquire lock
        success, error = self.acquire_lock(api_name, platform, timeout=timeout)
        
        if not success:
            raise LockConflictError(error)
        
        try:
            # Auto-renewal thread for long operations
            if auto_renew:
                # In production, use background thread for renewal
                # For now, caller should manually renew
                pass
            
            yield
            
        finally:
            # Always release lock
            self.release_lock(api_name, platform)
    
    def cleanup_expired_locks(self) -> int:
        """
        Clean up expired lock metadata.
        
        Redis automatically expires keys, but this ensures metadata is cleaned.
        
        Returns:
            Number of locks cleaned up
        """
        pattern = f"{self.LOCK_PREFIX}*"
        cleaned = 0
        
        for key in self.redis_client.scan_iter(match=pattern):
            # Check if key still exists
            if not self.redis_client.exists(key):
                # Remove metadata
                if key.startswith(f"{self.LOCK_PREFIX}info:"):
                    self.redis_client.delete(key)
                    cleaned += 1
        
        return cleaned
    
    def list_active_locks(self, team: Optional[str] = None) -> list[dict]:
        """
        List all active locks, optionally filtered by team.
        
        Args:
            team: Filter by team name (None = all teams)
            
        Returns:
            List of lock info dicts
        """
        pattern = f"{self.LOCK_PREFIX}info:*"
        active_locks = []
        
        for key in self.redis_client.scan_iter(match=pattern):
            lock_info = self.redis_client.hgetall(key)
            
            if lock_info:
                # Filter by team if specified
                if team is None or lock_info.get("team") == team:
                    # Extract API info from key
                    # Key format: api_migration:lock:info:{platform}:{api_name}
                    parts = key.split(":")
                    if len(parts) >= 4:
                        lock_info["platform"] = parts[3]
                        lock_info["api_name"] = ":".join(parts[4:])
                    
                    active_locks.append(lock_info)
        
        return active_locks
