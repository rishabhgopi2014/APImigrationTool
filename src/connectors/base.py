"""
Base Connector for Platform API Discovery

Abstract base class defining interface for all platform connectors.
Ensures consistent API discovery across APIC, MuleSoft, Kafka, and Swagger.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DiscoveredAPI:
    """Represents a discovered API from any platform"""
    # Core identification
    name: str
    platform: str  # apic, mulesoft, kafka, swagger
    
    # API details
    base_path: str
    version: str
    description: str
    
    # Organizational metadata
    catalog: str = "default"  # APIC catalog name
    collection: str = "uncategorized"  # APIC collection/product name
    
    # Ownership (may come from platform or be inferred)
    owner_team: Optional[str] = None
    owner_domain: Optional[str] = None
    
    # Technical details
    tags: List[str] = None  # API tags/labels
    protocol: Optional[str] = None  # HTTP, gRPC, Kafka, etc.
    auth_methods: List[str] = None  # OAuth, JWT, API Key, mTLS, etc.
    
    # Traffic metrics (if available)
    avg_requests_per_day: Optional[int] = None
    avg_latency_ms: Optional[int] = None
    error_rate: Optional[float] = None
    
    # Platform-specific metadata (stored as JSONB in database)
    legacy_metadata: Dict[str, Any] = None
    
    # Discovery metadata
    discovered_at: datetime = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.tags is None:
            self.tags = []
        if self.auth_methods is None:
            self.auth_methods = []
        if self.legacy_metadata is None:
            self.legacy_metadata = {}
        if self.discovered_at is None:
            self.discovered_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "name": self.name,
            "platform": self.platform,
            "base_path": self.base_path,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "owner_team": self.owner_team,
            "owner_domain": self.owner_domain,
            "protocol": self.protocol,
            "auth_methods": self.auth_methods,
            "avg_requests_per_day": self.avg_requests_per_day,
            "avg_latency_ms": self.avg_latency_ms,
            "error_rate": self.error_rate,
            "legacy_metadata": self.legacy_metadata,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None
        }


class PlatformConnector(ABC):
    """
    Abstract base class for platform connectors.
    
    All connectors must implement:
    - connect(): Authenticate and establish connection
    - discover_apis(): Discover APIs matching filters
    - get_api_details(): Get detailed info for specific API
    """
    
    def __init__(
        self,
        platform_name: str,
        credentials: Dict[str, Any],
        rate_limit: Optional[int] = 10
    ):
        """
        Initialize platform connector.
        
        Args:
            platform_name: Platform identifier (apic, mulesoft, etc.)
            credentials: Authentication credentials (URL, token, username/password)
            rate_limit: Max requests per second to platform API
        """
        self.platform_name = platform_name
        self.credentials = credentials
        self.rate_limit = rate_limit
        self.connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Authenticate and establish connection to platform.
        
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: If authentication fails
        """
        pass
    
    @abstractmethod
    def discover_apis(
        self,
        filters: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[DiscoveredAPI]:
        """
        Discover APIs from platform matching filters.
        
        Args:
            filters: Include patterns (glob or regex)
            exclude_patterns: Exclude patterns
            tags: Filter by tags
            
        Returns:
            List of DiscoveredAPI objects
        """
        pass
    
    @abstractmethod
    def get_api_details(self, api_name: str) -> Optional[DiscoveredAPI]:
        """
        Get detailed information for a specific API.
        
        Args:
            api_name: API identifier
            
        Returns:
            DiscoveredAPI object or None if not found
        """
        pass
    
    def disconnect(self):
        """Clean up connection resources"""
        self.connected = False
    
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """
        Test platform connection.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            success = self.connect()
            return True, None if success else False, "Connection failed"
        except Exception as e:
            return False, str(e)
    
    def get_platform_info(self) -> Dict[str, Any]:
        """
        Get platform information.
        
        Returns:
            Platform metadata dict
        """
        return {
            "platform": self.platform_name,
            "connected": self.connected,
            "credentials_configured": bool(self.credentials),
            "rate_limit": self.rate_limit
        }
