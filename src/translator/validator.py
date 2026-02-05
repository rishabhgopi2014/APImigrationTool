"""
Validation utilities for generated Gloo Gateway configs.

Ensures correctness before deployment:
- Schema validation against Gloo CRDs
- Kubernetes dry-run testing
- Configuration sanity checks
"""

import yaml
import jsonschema
from typing import Dict, Any, List, Tuple
import subprocess
import tempfile
import os


class GlooConfigValidator:
    """
    Validates generated Gloo Gateway configurations
    against official Gloo CRD schemas.
    """
    
    def __init__(self):
        """Initialize validator with Gloo CRD schemas"""
        self.schemas = self._load_gloo_schemas()
    
    def _load_gloo_schemas(self) -> Dict[str, Any]:
        """
        Load Gloo Gateway CRD JSON schemas.
        
        In production, these should be fetched from:
        https://github.com/solo-io/gloo/tree/master/install/helm/gloo/crds
        """
        # Simplified schemas for demonstration
        # In production, use full CRD schemas from Solo.io
        return {
            "VirtualService": {
                "type": "object",
                "required": ["apiVersion", "kind", "metadata", "spec"],
                "properties": {
                    "apiVersion": {"type": "string", "enum": ["gateway.solo.io/v1"]},
                    "kind": {"type": "string", "enum": ["VirtualService"]},
                    "metadata": {
                        "type": "object",
                        "required": ["name", "namespace"]
                    },
                    "spec": {
                        "type": "object",
                        "required": ["virtualHost"]
                    }
                }
            },
            "Upstream": {
                "type": "object",
                "required": ["apiVersion", "kind", "metadata", "spec"],
                "properties": {
                    "apiVersion": {"type": "string", "enum": ["gloo.solo.io/v1"]},
                    "kind": {"type": "string", "enum": ["Upstream"]},
                    "metadata": {
                        "type": "object",
                        "required": ["name", "namespace"]
                    },
                    "spec": {"type": "object"}
                }
            },
            "AuthConfig": {
                "type": "object",
                "required": ["apiVersion", "kind", "metadata", "spec"],
                "properties": {
                    "apiVersion": {"type": "string", "enum": ["enterprise.gloo.solo.io/v1"]},
                    "kind": {"type": "string", "enum": ["AuthConfig"]},
                    "metadata": {
                        "type": "object",
                        "required": ["name", "namespace"]
                    },
                    "spec": {
                        "type": "object",
                        "required": ["configs"]
                    }
                }
            },
            "RateLimitConfig": {
                "type": "object",
                "required": ["apiVersion", "kind", "metadata", "spec"],
                "properties": {
                    "apiVersion": {"type": "string", "enum": ["ratelimit.solo.io/v1alpha1"]},
                    "kind": {"type": "string", "enum": ["RateLimitConfig"]},
                    "metadata": {
                        "type": "object",
                        "required": ["name", "namespace"]
                    },
                    "spec": {"type": "object"}
                }
            }
        }
    
    def validate_yaml(self, yaml_content: str, resource_type: str) -> Tuple[bool, List[str]]:
        """
        Validate YAML against Gloo CRD schema.
        
        Args:
            yaml_content: YAML string to validate
            resource_type: Type of resource (VirtualService, Upstream, etc.)
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            # Parse YAML
            config = yaml.safe_load(yaml_content)
            
            # Get schema
            if resource_type not in self.schemas:
                errors.append(f"Unknown resource type: {resource_type}")
                return False, errors
            
            schema = self.schemas[resource_type]
            
            # Validate against schema
            try:
                jsonschema.validate(config, schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Schema validation failed: {e.message}")
                errors.append(f"Path: {'.'.join(str(p) for p in e.path)}")
                return False, errors
            
            # Additional sanity checks
            sanity_errors = self._sanity_checks(config, resource_type)
            if sanity_errors:
                errors.extend(sanity_errors)
                return False, errors
            
            return True, []
            
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML syntax: {str(e)}")
            return False, errors
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return False, errors
    
    def _sanity_checks(self, config: Dict[str, Any], resource_type: str) -> List[str]:
        """
        Additional sanity checks beyond schema validation.
        
        Args:
            config: Parsed config dict
            resource_type: Type of resource
            
        Returns:
            List of error messages (empty if all checks pass)
        """
        errors = []
        
        if resource_type == "VirtualService":
            # Check routes exist
            routes = config.get("spec", {}).get("virtualHost", {}).get("routes", [])
            if not routes:
                errors.append("VirtualService has no routes defined")
            
            # Check each route has matcher and action
            for idx, route in enumerate(routes):
                if "matchers" not in route:
                    errors.append(f"Route {idx} missing matchers")
                if "routeAction" not in route and "redirectAction" not in route:
                    errors.append(f"Route {idx} missing action")
        
        elif resource_type == "Upstream":
            # Check backend is defined
            spec = config.get("spec", {})
            if not any(k in spec for k in ["static", "kube", "aws"]):
                errors.append("Upstream missing backend definition (static/kube/aws)")
        
        elif resource_type == "AuthConfig":
            # Check at least one auth method configured
            configs = config.get("spec", {}).get("configs", [])
            if not configs:
                errors.append("AuthConfig has no auth methods configured")
        
        return errors
    
    def dry_run_kubectl(self, yaml_content: str) -> Tuple[bool, str]:
        """
        Test applying config with kubectl dry-run.
        
        Requires kubectl and access to a Kubernetes cluster.
        
        Args:
            yaml_content: YAML to test
            
        Returns:
            Tuple of (success, output_message)
        """
        try:
            # Write to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(yaml_content)
                temp_file = f.name
            
            try:
                # Run kubectl dry-run
                result = subprocess.run(
                    ['kubectl', 'apply', '-f', temp_file, '--dry-run=server'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    return True, result.stdout
                else:
                    return False, result.stderr
                    
            finally:
                # Clean up temp file
                os.unlink(temp_file)
                
        except subprocess.TimeoutExpired:
            return False, "kubectl command timed out"
        except FileNotFoundError:
            return False, "kubectl not found in PATH"
        except Exception as e:
            return False, f"Error running kubectl: {str(e)}"
    
    def validate_all(self, yaml_files: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate all generated YAML files.
        
        Args:
            yaml_files: Dict of {filename: yaml_content}
            
        Returns:
            Validation results dict
        """
        results = {
            "overall_valid": True,
            "files": {}
        }
        
        for filename, content in yaml_files.items():
            # Determine resource type from filename
            if "virtualservice" in filename.lower():
                resource_type = "VirtualService"
            elif "upstream" in filename.lower():
                resource_type = "Upstream"
            elif "authconfig" in filename.lower():
                resource_type = "AuthConfig"
            elif "ratelimit" in filename.lower():
                resource_type = "RateLimitConfig"
            else:
                results["files"][filename] = {
                    "valid": False,
                    "errors": ["Unknown resource type from filename"]
                }
                results["overall_valid"] = False
                continue
            
            # Validate
            is_valid, errors = self.validate_yaml(content, resource_type)
            
            results["files"][filename] = {
                "valid": is_valid,
                "resource_type": resource_type,
                "errors": errors
            }
            
            if not is_valid:
                results["overall_valid"] = False
        
        return results


def print_validation_report(results: Dict[str, Any]):
    """
    Print a formatted validation report.
    
    Args:
        results: Results from validate_all()
    """
    print("\n" + "="*60)
    print("  GLOO CONFIG VALIDATION REPORT")
    print("="*60)
    
    for filename, file_results in results["files"].items():
        status = "✅ VALID" if file_results["valid"] else "❌ INVALID"
        print(f"\n{filename}: {status}")
        print(f"  Resource Type: {file_results.get('resource_type', 'Unknown')}")
        
        if file_results.get("errors"):
            print("  Errors:")
            for error in file_results["errors"]:
                print(f"    - {error}")
    
    print("\n" + "="*60)
    if results["overall_valid"]:
        print("✅ ALL CONFIGS VALID - Safe to deploy!")
    else:
        print("❌ VALIDATION FAILED - Fix errors before deploying!")
    print("="*60 + "\n")


# Example usage
if __name__ == "__main__":
    # Test validation
    validator = GlooConfigValidator()
    
    test_vs = """
apiVersion: gateway.solo.io/v1
kind: VirtualService
metadata:
  name: test-api-vs
  namespace: gloo-system
spec:
  virtualHost:
    domains:
      - "test.company.com"
    routes:
      - matchers:
          - prefix: /api/v1
        routeAction:
          single:
            upstream:
              name: test-upstream
              namespace: gloo-system
"""
    
    is_valid, errors = validator.validate_yaml(test_vs, "VirtualService")
    
    if is_valid:
        print("✅ Validation passed!")
    else:
        print("❌ Validation failed:")
        for error in errors:
            print(f"  - {error}")
