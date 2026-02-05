"""
API Filter Engine

Provides flexible filtering for API discovery based on:
- Glob patterns (e.g., "payment-*", "*-gateway")
- Regular expressions
- Tags
- Custom predicates
- Ownership metadata

Ensures developers only discover and migrate APIs within their domain.
"""

import fnmatch
import re
from typing import Any, Callable, Dict, List, Optional


class APIMetadata:
    """Represents API metadata for filtering"""
    
    def __init__(
        self,
        name: str,
        platform: str,
        tags: Optional[List[str]] = None,
        owner_team: Optional[str] = None,
        owner_domain: Optional[str] = None,
        path: Optional[str] = None,
        version: Optional[str] = None,
        **extra_metadata
    ):
        self.name = name
        self.platform = platform
        self.tags = tags or []
        self.owner_team = owner_team
        self.owner_domain = owner_domain
        self.path = path
        self.version = version
        self.extra = extra_metadata

    def __repr__(self):
        return f"APIMetadata(name='{self.name}', platform='{self.platform}')"


class FilterEngine:
    """
    Multi-criteria API filtering engine for selective discovery.
    
    Supports:
    - Glob patterns (payment-*, *-api, checkout-*)
    - Regular expressions (^/api/v2/.*)
    - Tag-based filtering
    - Ownership filtering (team, domain)
    - Exclude patterns
    - Custom predicates
    """
    
    def __init__(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        owner_team: Optional[str] = None,
        owner_domain: Optional[str] = None,
        custom_predicates: Optional[List[Callable[[APIMetadata], bool]]] = None
    ):
        """
        Initialize filter engine.
        
        Args:
            include_patterns: Glob or regex patterns to include
            exclude_patterns: Glob or regex patterns to exclude
            tags: Required tags for inclusion
            owner_team: Filter by owner team
            owner_domain: Filter by owner domain
            custom_predicates: Custom filter functions
        """
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.tags = set(tags) if tags else set()
        self.owner_team = owner_team
        self.owner_domain = owner_domain
        self.custom_predicates = custom_predicates or []

    @staticmethod
    def _is_regex(pattern: str) -> bool:
        """Check if pattern is a regex (contains special regex chars)"""
        # Simple heuristic: if it has regex special chars beyond glob *, it's regex
        regex_chars = set(r'.^$+?{}[]\|()')
        return any(char in pattern for char in regex_chars)

    @staticmethod
    def _matches_pattern(text: str, pattern: str) -> bool:
        """
        Match text against pattern (glob or regex).
        
        Auto-detects if pattern is glob or regex.
        """
        if FilterEngine._is_regex(pattern):
            # Treat as regex
            try:
                return bool(re.search(pattern, text))
            except re.error:
                # Invalid regex, fall back to glob
                return fnmatch.fnmatch(text, pattern)
        else:
            # Treat as glob pattern
            return fnmatch.fnmatch(text, pattern)

    def matches_include_patterns(self, api: APIMetadata) -> bool:
        """
        Check if API matches any include pattern.
        
        Checks against API name and path (if available).
        """
        if not self.include_patterns:
            # No include patterns = include all
            return True
        
        # Check against name and path
        search_fields = [api.name]
        if api.path:
            search_fields.append(api.path)
        
        for field in search_fields:
            for pattern in self.include_patterns:
                if self._matches_pattern(field, pattern):
                    return True
        
        return False

    def matches_exclude_patterns(self, api: APIMetadata) -> bool:
        """Check if API matches any exclude pattern"""
        if not self.exclude_patterns:
            return False
        
        search_fields = [api.name]
        if api.path:
            search_fields.append(api.path)
        
        for field in search_fields:
            for pattern in self.exclude_patterns:
                if self._matches_pattern(field, pattern):
                    return True
        
        return False

    def matches_tags(self, api: APIMetadata) -> bool:
        """Check if API has all required tags"""
        if not self.tags:
            return True
        
        api_tags = set(api.tags)
        return self.tags.issubset(api_tags)

    def matches_ownership(self, api: APIMetadata) -> bool:
        """Check if API matches ownership criteria"""
        if self.owner_team and api.owner_team != self.owner_team:
            return False
        
        if self.owner_domain and api.owner_domain != self.owner_domain:
            return False
        
        return True

    def matches_custom_predicates(self, api: APIMetadata) -> bool:
        """Check if API matches all custom predicates"""
        return all(predicate(api) for predicate in self.custom_predicates)

    def matches(self, api: APIMetadata) -> bool:
        """
        Check if API passes all filter criteria.
        
        Returns True if API should be included in discovery.
        """
        # Must match include patterns
        if not self.matches_include_patterns(api):
            return False
        
        # Must NOT match exclude patterns
        if self.matches_exclude_patterns(api):
            return False
        
        # Must have required tags
        if not self.matches_tags(api):
            return False
        
        # Must match ownership
        if not self.matches_ownership(api):
            return False
        
        # Must pass custom predicates
        if not self.matches_custom_predicates(api):
            return False
        
        return True

    def filter(self, apis: List[APIMetadata]) -> List[APIMetadata]:
        """
        Filter a list of APIs.
        
        Args:
            apis: List of API metadata
            
        Returns:
            Filtered list of APIs matching all criteria
        """
        return [api for api in apis if self.matches(api)]

    def __repr__(self):
        return (
            f"FilterEngine(include={self.include_patterns}, "
            f"exclude={self.exclude_patterns}, tags={self.tags})"
        )


class PlatformFilterEngine:
    """
    Platform-specific filter engine that combines config-based filters
    with platform-specific logic.
    """
    
    def __init__(self, platform: str, platform_config: Dict[str, Any], owner_config: Dict[str, Any]):
        """
        Initialize platform filter engine from configuration.
        
        Args:
            platform: Platform name (apic, mulesoft, kafka, swagger)
            platform_config: Platform discovery configuration
            owner_config: Owner metadata from config
        """
        self.platform = platform
        self.enabled = platform_config.get("enabled", False)
        
        # Create base filter engine
        self.filter_engine = FilterEngine(
            include_patterns=platform_config.get("filters", []),
            exclude_patterns=platform_config.get("exclude_patterns", []),
            tags=platform_config.get("tags", []),
            owner_team=owner_config.get("team"),
            owner_domain=owner_config.get("domain")
        )

    def is_enabled(self) -> bool:
        """Check if discovery is enabled for this platform"""
        return self.enabled

    def filter(self, apis: List[APIMetadata]) -> List[APIMetadata]:
        """Filter APIs for this platform"""
        if not self.enabled:
            return []
        
        return self.filter_engine.filter(apis)
