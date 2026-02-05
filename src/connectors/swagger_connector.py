"""
Swagger/OpenAPI Connector

Discovers APIs from Swagger/OpenAPI specifications.
Supports loading from URLs or local files.
"""

import requests
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path
from .base import PlatformConnector, DiscoveredAPI
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename


class SwaggerConnector(PlatformConnector):
    """
    Swagger/OpenAPI connector for API discovery.
    
    Loads and parses OpenAPI specifications from URLs or files.
    """
    
    def __init__(self, credentials: Dict[str, Any], rate_limit: int = 10):
        """
        Initialize Swagger connector.
        
        Args:
            credentials: Dict with 'url' (spec URL) or 'files' (list of file paths)
            rate_limit: Max requests per second
        """
        super().__init__("swagger", credentials, rate_limit)
        self.spec_url = credentials.get("url")
        self.spec_files = credentials.get("files", [])
        self.token = credentials.get("token")  # For accessing private spec repos
    
    def connect(self) -> bool:
        """
        Test connection to Swagger/OpenAPI sources.
        
        Returns:
            True if specs are accessible
        """
        try:
            if self.spec_url:
                # Test URL accessibility
                headers = {}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"
                
                response = requests.head(self.spec_url, headers=headers, timeout=10)
                if response.status_code not in [200, 302]:
                    raise ConnectionError(f"Cannot access spec URL: {self.spec_url}")
            
            if self.spec_files:
                # Test file accessibility
                for file_path in self.spec_files:
                    if not Path(file_path).exists():
                        raise ConnectionError(f"Spec file not found: {file_path}")
            
            self.connected = True
            return True
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Swagger specs: {e}")
    
    def discover_apis(
        self,
        filters: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[DiscoveredAPI]:
        """
        Discover APIs from OpenAPI specifications.
        
        Args:
            filters: API name/path patterns to include
            exclude_patterns: Patterns to exclude
            tags: Filter by tags
            
        Returns:
            List of discovered APIs
        """
        if not self.connected:
            self.connect()
        
        discovered_apis = []
        
        # Load specs from URL
        if self.spec_url:
            spec = self._load_spec_from_url(self.spec_url)
            if spec:
                api = self._convert_spec_to_api(spec, self.spec_url)
                discovered_apis.append(api)
        
        # Load specs from files
        for file_path in self.spec_files:
            spec = self._load_spec_from_file(file_path)
            if spec:
                api = self._convert_spec_to_api(spec, file_path)
                discovered_apis.append(api)
        
        return discovered_apis
    
    def _load_spec_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Load OpenAPI spec from URL"""
        try:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Try JSON first, then YAML
                try:
                    return response.json()
                except:
                    return yaml.safe_load(response.text)
            else:
                print(f"Failed to load spec from {url}: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error loading spec from {url}: {e}")
            return None
    
    def _load_spec_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load OpenAPI spec from file"""
        try:
            path = Path(file_path)
            
            with open(path, 'r') as f:
                if path.suffix in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                else:
                    import json
                    return json.load(f)
                    
        except Exception as e:
            print(f"Error loading spec from {file_path}: {e}")
            return None
    
    def _convert_spec_to_api(self, spec: Dict[str, Any], source: str) -> DiscoveredAPI:
        """Convert OpenAPI spec to DiscoveredAPI"""
        info = spec.get("info", {})
        servers = spec.get("servers", [])
        
        # Extract API name and version
        name = info.get("title", "Unknown API")
        version = info.get("version", "1.0.0")
        description = info.get("description", "")
        
        # Extract base path from servers
        base_path = None
        if servers:
            base_path = servers[0].get("url", "")
        
        # Extract tags
        tags = []
        if "tags" in spec:
            tags = [tag.get("name") for tag in spec.get("tags", [])]
        
        # Detect auth methods from security schemes
        auth_methods = []
        if "components" in spec and "securitySchemes" in spec["components"]:
            for scheme_name, scheme in spec["components"]["securitySchemes"].items():
                auth_type = scheme.get("type")
                if auth_type == "oauth2":
                    auth_methods.append("oauth")
                elif auth_type == "http":
                    scheme_name = scheme.get("scheme", "").lower()
                    if scheme_name == "bearer":
                        auth_methods.append("jwt")
                    else:
                        auth_methods.append("http-basic")
                elif auth_type == "apiKey":
                    auth_methods.append("api-key")
        
        return DiscoveredAPI(
            name=name,
            platform="swagger",
            base_path=base_path,
            version=version,
            description=description,
            tags=tags,
            protocol="HTTP",
            auth_methods=auth_methods,
            legacy_metadata={
                "source": source,
                "openapi_version": spec.get("openapi", spec.get("swagger", "unknown")),
                "paths": list(spec.get("paths", {}).keys()),
                "full_spec": spec
            }
        )
    
    def get_api_details(self, api_name: str) -> Optional[DiscoveredAPI]:
        """
        Get detailed information for a specific API.
        
        Args:
            api_name: API name
            
        Returns:
            DiscoveredAPI object or None
        """
        all_apis = self.discover_apis()
        
        for api in all_apis:
            if api.name == api_name:
                return api
        
        return None
    
    def validate_spec(self, spec: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate OpenAPI specification.
        
        Args:
            spec: OpenAPI spec dict
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            validate_spec(spec)
            return True, None
        except Exception as e:
            return False, str(e)
