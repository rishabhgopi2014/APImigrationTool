"""
API Ownership Manager

Tracks API ownership metadata (team, domain, component) and provides
isolation between different teams' migration workflows.

Ensures developers can only migrate APIs within their ownership scope.
"""

from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class OwnershipScope(Enum):
    """Ownership verification result"""
    OWNED = "owned"              # Developer owns this API
    SHARED = "shared"            # API is shared across teams
    NOT_OWNED = "not_owned"      # API belongs to another team
    UNASSIGNED = "unassigned"    # No ownership metadata


class APIOwnership:
    """Represents ownership metadata for an API"""
    
    def __init__(
        self,
        api_name: str,
        platform: str,
        team: Optional[str] = None,
        domain: Optional[str] = None,
        component: Optional[str] = None,
        contact: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.api_name = api_name
        self.platform = platform
        self.team = team
        self.domain = domain
        self.component = component
        self.contact = contact
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def is_owned_by(self, team: str, domain: Optional[str] = None) -> bool:
        """
        Check if API is owned by specified team/domain.
        
        Args:
            team: Team name to check
            domain: Optional domain name to check
            
        Returns:
            True if ownership matches
        """
        if not self.team:
            return False  # Unassigned
        
        if self.team != team:
            return False
        
        if domain and self.domain and self.domain != domain:
            return False
        
        return True

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "api_name": self.api_name,
            "platform": self.platform,
            "team": self.team,
            "domain": self.domain,
            "component": self.component,
            "contact": self.contact,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def from_dict(data: Dict) -> "APIOwnership":
        """Create from dictionary"""
        return APIOwnership(
            api_name=data["api_name"],
            platform=data["platform"],
            team=data.get("team"),
            domain=data.get("domain"),
            component=data.get("component"),
            contact=data.get("contact"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
        )


class OwnershipManager:
    """
    Manages API ownership metadata and provides ownership verification.
    
    In production, this would integrate with a database.
    For now, implements in-memory storage.
    """
    
    def __init__(self, current_team: str, current_domain: Optional[str] = None):
        """
        Initialize ownership manager for a specific team.
        
        Args:
            current_team: Current developer's team name
            current_domain: Current developer's domain name
        """
        self.current_team = current_team
        self.current_domain = current_domain
        self._ownership_db: Dict[str, APIOwnership] = {}

    def _api_key(self, api_name: str, platform: str) -> str:
        """Generate unique key for API"""
        return f"{platform}:{api_name}"

    def register_ownership(
        self,
        api_name: str,
        platform: str,
        team: Optional[str] = None,
        domain: Optional[str] = None,
        component: Optional[str] = None,
        contact: Optional[str] = None
    ) -> APIOwnership:
        """
        Register or update API ownership metadata.
        
        Args:
            api_name: API name
            platform: Platform name
            team: Owning team (defaults to current team)
            domain: Owning domain (defaults to current domain)
            component: Component name
            contact: Contact email
            
        Returns:
            APIOwnership object
        """
        ownership = APIOwnership(
            api_name=api_name,
            platform=platform,
            team=team or self.current_team,
            domain=domain or self.current_domain,
            component=component,
            contact=contact
        )
        
        key = self._api_key(api_name, platform)
        self._ownership_db[key] = ownership
        
        return ownership

    def get_ownership(self, api_name: str, platform: str) -> Optional[APIOwnership]:
        """
        Get ownership metadata for an API.
        
        Args:
            api_name: API name
            platform: Platform name
            
        Returns:
            APIOwnership object or None if not found
        """
        key = self._api_key(api_name, platform)
        return self._ownership_db.get(key)

    def verify_ownership(self, api_name: str, platform: str) -> OwnershipScope:
        """
        Verify if current developer/team owns this API.
        
        Args:
            api_name: API name
            platform: Platform name
            
        Returns:
            OwnershipScope enum indicating ownership status
        """
        ownership = self.get_ownership(api_name, platform)
        
        if not ownership:
            return OwnershipScope.UNASSIGNED
        
        if ownership.is_owned_by(self.current_team, self.current_domain):
            return OwnershipScope.OWNED
        
        # Check if it's a shared API (no specific domain)
        if ownership.team == self.current_team and not ownership.domain:
            return OwnershipScope.SHARED
        
        return OwnershipScope.NOT_OWNED

    def can_migrate(self, api_name: str, platform: str) -> tuple[bool, str]:
        """
        Check if current developer can migrate this API.
        
        Args:
            api_name: API name
            platform: Platform name
            
        Returns:
            Tuple of (can_migrate, reason)
        """
        scope = self.verify_ownership(api_name, platform)
        
        if scope == OwnershipScope.OWNED:
            return True, "API is owned by your team/domain"
        
        if scope == OwnershipScope.SHARED:
            return True, "API is shared within your team"
        
        if scope == OwnershipScope.UNASSIGNED:
            # Allow claiming unassigned APIs
            return True, "API is unassigned, will be claimed by your team"
        
        if scope == OwnershipScope.NOT_OWNED:
            ownership = self.get_ownership(api_name, platform)
            return False, f"API is owned by {ownership.team} (domain: {ownership.domain})"
        
        return False, "Unknown ownership status"

    def list_owned_apis(self) -> List[APIOwnership]:
        """
        List all APIs owned by current team/domain.
        
        Returns:
            List of APIOwnership objects
        """
        owned = []
        
        for ownership in self._ownership_db.values():
            if ownership.is_owned_by(self.current_team, self.current_domain):
                owned.append(ownership)
        
        return owned

    def list_all_apis(self) -> List[APIOwnership]:
        """List all APIs in ownership database"""
        return list(self._ownership_db.values())

    def bulk_register(self, apis: List[Dict]) -> List[APIOwnership]:
        """
        Bulk register ownership for multiple APIs.
        
        Args:
            apis: List of API metadata dicts
            
        Returns:
            List of registered APIOwnership objects
        """
        registered = []
        
        for api_data in apis:
            ownership = self.register_ownership(
                api_name=api_data["api_name"],
                platform=api_data["platform"],
                team=api_data.get("team"),
                domain=api_data.get("domain"),
                component=api_data.get("component"),
                contact=api_data.get("contact")
            )
            registered.append(ownership)
        
        return registered
