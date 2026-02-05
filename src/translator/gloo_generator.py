"""
Gloo Gateway Config Generator

Translates APIC API definitions to Gloo Gateway Kubernetes resources:
- VirtualService (routing)
- Upstream (backend targets)
- AuthConfig (OAuth, JWT, API Key)
- RateLimitConfig
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import yaml
from ..connectors.base import DiscoveredAPI


@dataclass
class GlooConfig:
    """Generated Gloo Gateway configuration"""
    virtual_service: Dict[str, Any]
    upstream: Dict[str, Any]
    auth_config: Optional[Dict[str, Any]] = None
    rate_limit_config: Optional[Dict[str, Any]] = None
    
    def to_yaml_files(self) -> Dict[str, str]:
        """Convert to separate YAML files"""
        files = {}
        
        files["virtualservice.yaml"] = yaml.dump(
            self.virtual_service,
            default_flow_style=False,
            sort_keys=False
        )
        
        files["upstream.yaml"] = yaml.dump(
            self.upstream,
            default_flow_style=False,
            sort_keys=False
        )
        
        if self.auth_config:
            files["authconfig.yaml"] = yaml.dump(
                self.auth_config,
                default_flow_style=False,
                sort_keys=False
            )
        
        if self.rate_limit_config:
            files["ratelimit.yaml"] = yaml.dump(
                self.rate_limit_config,
                default_flow_style=False,
                sort_keys=False
            )
        
        return files


class GlooConfigGenerator:
    """
    Translator from APIC API definitions to Gloo Gateway configs.
    
    Generates Kubernetes CRDs for Gloo Gateway.
    """
    
    def __init__(self, namespace: str = "gloo-system"):
        """
        Initialize generator.
        
        Args:
            namespace: Kubernetes namespace for Gloo resources
        """
        self.namespace = namespace
    
    def generate(self, api: DiscoveredAPI, backend_host: str = None) -> GlooConfig:
        """
        Generate Gloo Gateway configuration from discovered API.
        
        Args:
            api: Discovered API metadata
            backend_host: Backend service host (e.g., "legacy-apic.company.com")
            
        Returns:
            GlooConfig object with all resources
        """
        # Default backend from APIC metadata or use provided
        if not backend_host:
            backend_host = api.legacy_metadata.get("apic_url", "apic-gateway.company.com")
        
        # Generate each component
        virtual_service = self._generate_virtual_service(api)
        upstream = self._generate_upstream(api, backend_host)
        auth_config = self._generate_auth_config(api) if api.auth_methods else None
        rate_limit_config = self._generate_rate_limit_config(api)
        
        return GlooConfig(
            virtual_service=virtual_service,
            upstream=upstream,
            auth_config=auth_config,
            rate_limit_config=rate_limit_config
        )
    
    def _generate_virtual_service(self, api: DiscoveredAPI) -> Dict[str, Any]:
        """Generate Gloo VirtualService for routing"""
        safe_name = api.name.replace("_", "-").lower()
        
        vs = {
            "apiVersion": "gateway.solo.io/v1",
            "kind": "VirtualService",
            "metadata": {
                "name": f"{safe_name}-vs",
                "namespace": self.namespace,
                "labels": {
                    "app": safe_name,
                    "platform": api.platform,
                    "team": api.owner_team or "unknown",
                    "domain": api.owner_domain or "unknown"
                },
                "annotations": {
                    "description": api.description or f"Auto-generated from {api.platform}",
                    "migration.tool": "api-migration-orchestrator",
                    "original.platform": api.platform
                }
            },
            "spec": {
                "virtualHost": {
                    "domains": [
                        f"{safe_name}.company.com",  # Customize domain
                        f"api.company.com"  # Share common gateway
                    ],
                    "routes": []
                }
            }
        }
        
        # Add routes from APIC endpoints
        endpoints = api.legacy_metadata.get("endpoints", [])
        if endpoints:
            for endpoint in endpoints:
                route = {
                    "matchers": [{
                        "prefix": endpoint.get("path", api.base_path),
                        "methods": [endpoint.get("method", "GET")]
                    }],
                    "routeAction": {
                        "single": {
                            "upstream": {
                                "name": f"{safe_name}-upstream",
                                "namespace": self.namespace
                            }
                        }
                    }
                }
                vs["spec"]["virtualHost"]["routes"].append(route)
        else:
            # Default route for entire base path
            vs["spec"]["virtualHost"]["routes"].append({
                "matchers": [{
                    "prefix": api.base_path or "/"
                }],
                "routeAction": {
                    "single": {
                        "upstream": {
                            "name": f"{safe_name}-upstream",
                            "namespace": self.namespace
                        }
                    }
                }
            })
        
        return vs
    
    def _generate_upstream(self, api: DiscoveredAPI, backend_host: str) -> Dict[str, Any]:
        """Generate Gloo Upstream for backend service"""
        safe_name = api.name.replace("_", "-").lower()
        
        upstream = {
            "apiVersion": "gloo.solo.io/v1",
            "kind": "Upstream",
            "metadata": {
                "name": f"{safe_name}-upstream",
                "namespace": self.namespace,
                "labels": {
                    "app": safe_name,
                    "platform": api.platform
                }
            },
            "spec": {
                "static": {
                    "hosts": [{
                        "addr": backend_host,
                        "port": 443
                    }]
                },
                "sslConfig": {
                    "sni": backend_host
                }
            }
        }
        
        return upstream
    
    def _generate_auth_config(self, api: DiscoveredAPI) -> Optional[Dict[str, Any]]:
        """Generate Gloo AuthConfig based on APIC auth methods"""
        if not api.auth_methods:
            return None
        
        safe_name = api.name.replace("_", "-").lower()
        auth_method = api.auth_methods[0].lower()  # Use first auth method
        
        auth_config = {
            "apiVersion": "enterprise.gloo.solo.io/v1",
            "kind": "AuthConfig",
            "metadata": {
                "name": f"{safe_name}-auth",
                "namespace": self.namespace
            },
            "spec": {
                "configs": []
            }
        }
        
        # OAuth2
        if "oauth" in auth_method:
            auth_config["spec"]["configs"].append({
                "oauth2": {
                    "oidcAuthorizationCode": {
                        "appUrl": f"https://{safe_name}.company.com",
                        "callbackPath": "/oauth/callback",
                        "clientId": "REPLACE_WITH_CLIENT_ID",
                        "clientSecretRef": {
                            "name": f"{safe_name}-oauth-secret",
                            "namespace": self.namespace
                        },
                        "issuerUrl": "https://auth.company.com",
                        "scopes": ["openid", "profile", "email"]
                    }
                }
            })
        
        # JWT
        elif "jwt" in auth_method:
            auth_config["spec"]["configs"].append({
                "jwt": {
                    "providers": {
                        "company-jwt": {
                            "issuer": "https://auth.company.com",
                            "jwks": {
                                "remote": {
                                    "url": "https://auth.company.com/.well-known/jwks.json",
                                    "upstreamRef": {
                                        "name": "auth-server",
                                        "namespace": self.namespace
                                    }
                                }
                            }
                        }
                    }
                }
            })
        
        # API Key
        elif "api-key" in auth_method or "apikey" in auth_method:
            auth_config["spec"]["configs"].append({
                "apiKeyAuth": {
                    "headerName": "X-API-Key",
                    "labelSelector": {
                        "app": safe_name
                    }
                }
            })
        
        # Basic Auth
        elif "basic" in auth_method or "http-basic" in auth_method:
            auth_config["spec"]["configs"].append({
                "basicAuth": {
                    "apr": {
                        "usersFromSecret": {
                            "name": f"{safe_name}-basic-auth",
                            "namespace": self.namespace
                        }
                    }
                }
            })
        
        return auth_config
    
    def _generate_rate_limit_config(self, api: DiscoveredAPI) -> Optional[Dict[str, Any]]:
        """Generate Gloo RateLimitConfig from APIC rate limits"""
        rate_limits = api.legacy_metadata.get("rate_limits", {})
        if not rate_limits:
            # Default rate limits based on traffic
            if api.avg_requests_per_day and api.avg_requests_per_day > 1_000_000:
                rate_limits = {"per_minute": 10000, "per_hour": 500000}
            else:
                rate_limits = {"per_minute": 1000, "per_hour": 50000}
        
        safe_name = api.name.replace("_", "-").lower()
        
        rl_config = {
            "apiVersion": "ratelimit.solo.io/v1alpha1",
            "kind": "RateLimitConfig",
            "metadata": {
                "name": f"{safe_name}-ratelimit",
                "namespace": self.namespace
            },
            "spec": {
                "raw": {
                    "descriptors": [{
                        "key": "generic_key",
                        "value": safe_name,
                        "rateLimit": {
                            "requestsPerUnit": rate_limits.get("per_minute", 1000),
                            "unit": "MINUTE"
                        }
                    }]
                }
            }
        }
        
        return rl_config
