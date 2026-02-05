"""
Mock APIC Data Generator

Generates realistic mock API data for testing without needing actual APIC connection.
Includes varied domains, traffic patterns, and risk levels.
"""

import random
from typing import List
from .base import DiscoveredAPI


class MockAPICData:
    """Generator for realistic mock APIC API data"""
    
    # Different business domains
    DOMAINS = {
        "customer": [
            "customer-profile-api",
            "customer-search-api",
            "customer-registration-api",
            "customer-preferences-api",
            "customer-notifications-api",
            "customer-address-api"
        ],
        "inventory": [
            "inventory-lookup-api",
            "inventory-sync-api",
            "inventory-allocation-api",
            "warehouse-stock-api",
            "product-availability-api"
        ],
        "order": [
            "order-create-api",
            "order-status-api",
            "order-fulfillment-api",
            "order-history-api",
            "order-tracking-api"
        ],
        "payment": [
            "payment-gateway-api",
            "payment-validation-api",
            "refund-processing-api",
            "payment-history-api"
        ],
        "shipping": [
            "shipping-calculation-api",
            "shipping-tracking-api",
            "carrier-integration-api",
            "delivery-schedule-api"
        ]
    }
    
    # Traffic patterns - realistic distribution
    TRAFFIC_PATTERNS = [
        # Critical APIs (very high traffic)
        {"min": 2_000_000, "max": 5_000_000, "error_rate": (0.001, 0.005), "latency": (80, 200)},
        # High traffic APIs
        {"min": 500_000, "max": 2_000_000, "error_rate": (0.001, 0.003), "latency": (50, 150)},
        # Medium traffic APIs
        {"min": 50_000, "max": 500_000, "error_rate": (0.0005, 0.002), "latency": (40, 100)},
        # Low traffic APIs
        {"min": 1_000, "max": 50_000, "error_rate": (0.0001, 0.001), "latency": (30, 80)},
    ]
    
    AUTH_METHODS = [
        ["oauth", "jwt"],
        ["jwt"],
        ["api-key"],
        ["api-key", "http-basic"],
        [],  # No auth
    ]
    
    @classmethod
    def generate_apis(cls, domain_filter: str = None, count: int = None) -> List[DiscoveredAPI]:
        """
        Generate mock APIC APIs.
        
        Args:
            domain_filter: Filter by domain (e.g., "customer-*")
            count: Number of APIs to generate (default: all matching)
            
        Returns:
            List of mock DiscoveredAPI objects
        """
        all_apis = []
        
        for domain, api_names in cls.DOMAINS.items():
            for api_name in api_names:
                # Apply domain filter if specified
                if domain_filter:
                    if domain_filter.endswith("*"):
                        prefix = domain_filter[:-1]
                        if not api_name.startswith(prefix):
                            continue
                    elif domain_filter != api_name:
                        continue
                
                # Generate traffic based on API importance
                traffic_pattern = random.choice(cls.TRAFFIC_PATTERNS)
                requests_per_day = random.randint(traffic_pattern["min"], traffic_pattern["max"])
                error_rate = random.uniform(*traffic_pattern["error_rate"])
                latency = random.randint(*traffic_pattern["latency"])
                
                # Assign auth methods
                auth_methods = random.choice(cls.AUTH_METHODS)
                
                # Create realistic API paths
                version = random.choice(["v1", "v2", "v3"])
                base_path = f"/{domain}/{version}"
                
                # Generate tags
                tags = [domain, "production"]
                if "api" in api_name:
                    tags.append("rest-api")
                if requests_per_day > 1_000_000:
                    tags.append("high-traffic")
                
                api = DiscoveredAPI(
                    name=api_name,
                    platform="apic",
                    base_path=base_path,
                    version=version,
                    description=f"Mock {api_name.replace('-', ' ').title()} for {domain} domain",
                    tags=tags,
                    owner_team=f"{domain}-team",
                    owner_domain=domain,
                    protocol="HTTP",
                    auth_methods=auth_methods,
                    avg_requests_per_day=requests_per_day,
                    avg_latency_ms=latency,
                    error_rate=error_rate,
                    legacy_metadata={
                        "apic_catalog": "production",
                        "apic_product": f"{domain}-product",
                        "endpoints": [
                            {"path": f"{base_path}/list", "method": "GET"},
                            {"path": f"{base_path}/create", "method": "POST"},
                            {"path": f"{base_path}/{{id}}", "method": "GET"},
                            {"path": f"{base_path}/{{id}}", "method": "PUT"},
                            {"path": f"{base_path}/{{id}}", "method": "DELETE"}
                        ],
                        "rate_limits": {
                            "per_minute": 1000 if requests_per_day > 500_000 else 100,
                            "per_hour": 50000 if requests_per_day > 500_000 else 5000
                        },
                        "cors_enabled": True,
                        "ssl_required": True
                    }
                )
                
                all_apis.append(api)
        
        # Apply count limit if specified
        if count:
            all_apis = all_apis[:count]
        
        return all_apis
    
    @classmethod
    def generate_for_team(cls, team: str, domain: str) -> List[DiscoveredAPI]:
        """
        Generate APIs for a specific team.
        
        Args:
            team: Team name (e.g., "customer-services")
            domain: Domain name (e.g., "customer")
            
        Returns:
            List of APIs for that domain
        """
        apis = []
        domain_key = domain.split("-")[0]  # Extract base domain
        
        if domain_key in cls.DOMAINS:
            for api_name in cls.DOMAINS[domain_key]:
                traffic_pattern = random.choice(cls.TRAFFIC_PATTERNS)
                requests_per_day = random.randint(traffic_pattern["min"], traffic_pattern["max"])
                error_rate = random.uniform(*traffic_pattern["error_rate"])
                latency = random.randint(*traffic_pattern["latency"])
                auth_methods = random.choice(cls.AUTH_METHODS)
                
                version = random.choice(["v1", "v2"])
                base_path = f"/{domain_key}/{version}"
                
                api = DiscoveredAPI(
                    name=api_name,
                    platform="apic",
                    base_path=base_path,
                    version=version,
                    description=f"{api_name.replace('-', ' ').title()}",
                    tags=[domain_key, "production", "rest-api"],
                    owner_team=team,
                    owner_domain=domain,
                    protocol="HTTP",
                    auth_methods=auth_methods,
                    avg_requests_per_day=requests_per_day,
                    avg_latency_ms=latency,
                    error_rate=error_rate,
                    legacy_metadata={
                        "apic_catalog": "production",
                        "apic_product": f"{domain_key}-apis"
                    }
                )
                apis.append(api)
        
        return apis
