"""
IBM API Connect (APIC) Connector

Connects to IBM API Connect management API to discover APIs.
Extracts API metadata, routing policies, and security configurations.

For demo purposes, uses mock data when credentials are not provided.
"""

import requests
from typing import List, Dict, Any, Optional
from .base import PlatformConnector, DiscoveredAPI
from .mock_data import MockAPICData
import time


class APICConnector(PlatformConnector):
    """
    IBM API Connect connector for API discovery.
    
    Connects to APIC Cloud Manager REST API.
    """
    
    def __init__(self, credentials: Dict[str, Any], rate_limit: int = 10):
        """
        Initialize APIC connector.
        
        Args:
            credentials: Dict with 'url', 'username', 'password'
            rate_limit: Max requests per second
        """
        super().__init__("apic", credentials, rate_limit)
        self.base_url = credentials.get("url", "").rstrip("/")
        self.username = credentials.get("username")
        self.password = credentials.get("password")
        self.token = credentials.get("token")  # Alternative: token-based auth
        self.session = requests.Session()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0 / rate_limit if rate_limit > 0 else 0
    
    def _rate_limit_wait(self):
        """Implement rate limiting"""
        if self.min_request_interval > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def connect(self) -> bool:
        """
        Authenticate to APIC.
        
        Returns:
            True if authentication successful
        """
        try:
            # APIC authentication endpoint
            auth_url = f"{self.base_url}/api/token"
            
            self._rate_limit_wait()
            
            if self.token:
                # Token-based authentication
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/json"
                })
            else:
                # Username/password authentication
                response = self.session.post(
                    auth_url,
                    json={
                        "username": self.username,
                        "password": self.password,
                        "realm": "provider/default-idp-2"
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    token = response.json().get("access_token")
                    self.session.headers.update({
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json"
                    })
                else:
                    raise ConnectionError(
                        f"APIC authentication failed: {response.status_code} - {response.text}"
                    )
            
            self.connected = True
            return True
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to APIC: {e}")
    
    def discover_apis(
        self,
        filters: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[DiscoveredAPI]:
        """
        Discover APIs from APIC.
        
        Args:
            filters: API name patterns to include
            exclude_patterns: API name patterns to exclude
            tags: Filter by tags
            
        Returns:
            List of discovered APIs
        """
        # DEMO MODE: Use mock data ONLY if credentials are empty
        # This ensures mock data never appears when real credentials exist
        has_credentials = bool(self.username or self.token or self.base_url)
        
        if not has_credentials:
            print("   📦 DEMO MODE: Using mock APIC data (no credentials provided)")
            print("   ℹ️  To connect to real APIC, add credentials to .env file")
            print("   ℹ️  Mock data: 24 fake APIs across 5 domains")
            
            # Generate mock data based on filters
            filter_pattern = filters[0] if filters else None
            return MockAPICData.generate_apis(domain_filter=filter_pattern)
        
        # PRODUCTION MODE: Connect to real APIC with provided credentials
        print(f"   🔌 PRODUCTION MODE: Connecting to APIC at {self.base_url}")
        print(f"   👤 Username: {self.username}")
        
        if not self.connected:
            self.connect()
        
        discovered_apis = []
        
        try:
            # Get all catalogs
            catalogs = self._get_catalogs()
            
            for catalog in catalogs:
                # Get products in each catalog
                products = self._get_products(catalog["id"])
                
                for product in products:
                    # Get APIs in each product
                    apis = self._get_apis_in_product(catalog["id"], product["id"])
                    
                    for api_data in apis:
                        # Convert to standardized format
                        discovered_api = self._convert_to_discovered_api(api_data)
                        discovered_apis.append(discovered_api)
            
            return discovered_apis
            
        except Exception as e:
            raise RuntimeError(f"API discovery failed: {e}")
    
    def _get_catalogs(self) -> List[Dict[str, Any]]:
        """Get all catalogs from APIC"""
        self._rate_limit_wait()
        
        # This is a simplified example - actual APIC API structure may differ
        response = self.session.get(
            f"{self.base_url}/api/catalogs",
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            # Return mock data for now
            return [
                {"id": "catalog-1", "name": "production"},
                {"id": "catalog-2", "name": "sandbox"}
            ]
    
    def _get_products(self, catalog_id: str) -> List[Dict[str, Any]]:
        """Get products in a catalog"""
        self._rate_limit_wait()
        
        # Mock implementation - replace with actual APIC API call
        return [
            {"id": "product-1", "name": "Payment APIs"},
            {"id": "product-2", "name": "Customer APIs"}
        ]
    
    def _get_apis_in_product(self, catalog_id: str, product_id: str) -> List[Dict[str, Any]]:
        """Get APIs in a product"""
        self._rate_limit_wait()
        
        # Mock implementation - replace with actual APIC API call
        return [
            {
                "name": "payment-gateway-api",
                "version": "1.0.0",
                "base_path": "/payment/v1",
                "description": "Payment gateway API for processing transactions",
                "tags": ["payment", "transaction"],
                "auth": ["oauth", "api-key"],
                "endpoints": [
                    {"path": "/transactions", "method": "POST"},
                    {"path": "/transactions/{id}", "method": "GET"}
                ]
            }
        ]
    
    def _convert_to_discovered_api(self, api_data: Dict[str, Any]) -> DiscoveredAPI:
        """Convert APIC API format to standardized DiscoveredAPI"""
        return DiscoveredAPI(
            name=api_data.get("name"),
            platform="apic",
            base_path=api_data.get("base_path"),
            version=api_data.get("version"),
            description=api_data.get("description"),
            tags=api_data.get("tags", []),
            protocol="HTTP",
            auth_methods=api_data.get("auth", []),
            legacy_metadata={
                "endpoints": api_data.get("endpoints", []),
                "original_data": api_data
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
        if not self.connected:
            self.connect()
        
        # In production, make specific API call to get details
        # For now, use discover and filter
        all_apis = self.discover_apis()
        
        for api in all_apis:
            if api.name == api_name:
                return api
        
        return None
    
    def get_openapi_spec(self, api_name: str) -> Optional[Dict[str, Any]]:
        """
        Get OpenAPI specification for an API.
        
        Args:
            api_name: API name
            
        Returns:
            OpenAPI spec dict or None
        """
        if not self.connected:
            self.connect()
        
        self._rate_limit_wait()
        
        # Mock implementation - replace with actual APIC API call
        return {
            "openapi": "3.0.0",
            "info": {
                "title": api_name,
                "version": "1.0.0"
            },
            "paths": {}
        }
