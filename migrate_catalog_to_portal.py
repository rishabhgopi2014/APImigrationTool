#!/usr/bin/env python3
"""
APIC Catalog to Gloo Portal Migration Tool

This script migrates APIC catalog structure (catalogs, collections, plans)
to Gloo Portal resources (Portals, API Products, Usage Plans).

Usage:
    python migrate_catalog_to_portal.py catalog-mapping.yaml ./portal-configs
"""

import yaml
import sys
from pathlib import Path


def migrate_catalog_to_portal(catalog_mapping_file, output_dir):
    """
    Migrate APIC catalogs and collections to Gloo Portal
    
    Args:
        catalog_mapping_file: Path to catalog-mapping.yaml
        output_dir: Directory to write Gloo Portal YAML files
    """
    
    print("=" * 70)
    print("  APIC Catalog → Gloo Portal Migration")
    print("=" * 70)
    print()
    
    # Load catalog mapping
    try:
        with open(catalog_mapping_file) as f:
            mapping = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {catalog_mapping_file}")
        print("\nCreate a catalog-mapping.yaml file first")
        print("See CATALOG_TO_PORTAL_MIGRATION.md for format")
        sys.exit(1)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    total_portals = 0
    total_products = 0
    total_plans = 0
    
    for catalog in mapping.get('catalogs', []):
        catalog_name = catalog['name']
        portal_name = catalog['portal_name']
        
        print(f"📋 Processing Catalog: {catalog_name}")
        print(f"   Portal Name: {portal_name}")
        
        # Create Portal resource
        portal = {
            'apiVersion': 'portal.gloo.solo.io/v1beta1',
            'kind': 'Portal',
            'metadata': {
                'name': portal_name,
                'namespace': 'gloo-portal',
                'labels': {
                    'apic-catalog': catalog_name
                }
            },
            'spec': {
                'displayName': f'{catalog_name.title()} API Portal',
                'description': catalog.get('description', f'Portal for {catalog_name} APIs'),
                'domains': catalog.get('domains', [f'{portal_name}.company.com']),
                'publishedApiProducts': []
            }
        }
        
        # Add branding if provided
        if 'branding' in catalog:
            if 'logo_url' in catalog['branding']:
                portal['spec']['banner'] = {
                    'fetchUrl': catalog['branding']['logo_url']
                }
            if 'primary_color' in catalog['branding']:
                portal['spec']['primaryColor'] = catalog['branding']['primary_color']
        
        # Add authentication if provided
        if 'auth' in catalog:
            if catalog['auth']['type'] == 'oidc':
                portal['spec']['oidcAuth'] = {
                    'clientId': catalog['auth']['client_id'],
                    'clientSecret': {
                        'name': catalog['auth']['secret_name'],
                        'namespace': 'gloo-portal'
                    },
                    'issuerUrl': catalog['auth']['issuer_url']
                }
        
        # Create API Products for each collection
        for collection in catalog.get('collections', []):
            collection_name = collection['name']
            product_name = collection['product_name']
            
            print(f"   📦 Collection: {collection_name} → Product: {product_name}")
            
            # Add to portal
            portal['spec']['publishedApiProducts'].append({
                'name': product_name,
                'namespace': 'gloo-portal'
            })
            
            # Create API Product
            api_product = {
                'apiVersion': 'portal.gloo.solo.io/v1beta1',
                'kind': 'APIProduct',
                'metadata': {
                    'name': product_name,
                    'namespace': 'gloo-portal',
                    'labels': {
                        'apic-catalog': catalog_name,
                        'apic-collection': product_name
                    }
                },
                'spec': {
                    'displayName': collection_name,
                    'description': collection.get('description', f'API Product for {collection_name}'),
                    'apis': [],
                    'usagePlans': []
                }
            }
            
            # Add APIs to product
            for api_name in collection.get('apis', []):
                api_product['spec']['apis'].append({
                    'apiRef': {
                        'name': f'{api_name}-vs',
                        'namespace': 'gloo-system'
                    }
                })
                print(f"      ├── API: {api_name}")
            
            # Add usage plans
            for plan in collection.get('plans', []):
                # Parse rate limit (e.g., "10000/day" -> 10000, DAY)
                rate_str = plan['rate_limit']
                if '/' in rate_str:
                    requests, unit = rate_str.split('/')
                    requests = int(requests)
                    unit = unit.upper()
                else:
                    # Default to no limit
                    requests = 1000000
                    unit = 'DAY'
                
                usage_plan = {
                    'name': plan['name'].lower().replace(' ', '-').replace('_', '-'),
                    'displayName': plan['name'],
                    'description': plan.get('description', f'{plan["name"]} plan with {rate_str} requests'),
                    'rateLimit': {
                        'requestsPerUnit': requests,
                        'unit': unit
                    }
                }
                
                # Add auth policy
                auth_type = plan.get('auth_type', 'apiKey')
                if auth_type == 'apiKey':
                    usage_plan['authPolicy'] = {'apiKey': {}}
                elif auth_type == 'oauth':
                    usage_plan['authPolicy'] = {
                        'oauth': {
                            'authorizationUrl': plan.get('oauth_auth_url', 'https://auth.company.com/oauth/authorize'),
                            'tokenUrl': plan.get('oauth_token_url', 'https://auth.company.com/oauth/token')
                        }
                    }
                
                api_product['spec']['usagePlans'].append(usage_plan)
                print(f"      └── Plan: {plan['name']} ({rate_str})")
                total_plans += 1
            
            # Write API Product
            product_file = output_path / f'{product_name}-product.yaml'
            with open(product_file, 'w') as f:
                yaml.dump(api_product, f, default_flow_style=False, sort_keys=False)
            print(f"   ✅ Created: {product_file.name}")
            total_products += 1
        
        # Write Portal
        portal_file = output_path / f'{portal_name}-portal.yaml'
        with open(portal_file, 'w') as f:
            yaml.dump(portal, f, default_flow_style=False, sort_keys=False)
        print(f"✅ Created: {portal_file.name}")
        print()
        total_portals += 1
    
    # Create deployment script
    deploy_script = output_path / 'deploy.sh'
    with open(deploy_script, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write('# Deploy Gloo Portal resources\n\n')
        f.write('echo "Deploying Gloo Portal resources..."\n\n')
        f.write('# Install Gloo Portal (if not already installed)\n')
        f.write('# helm install gloo-portal gloo-portal/gloo-portal -n gloo-portal --create-namespace --set licenseKey=$GLOO_LICENSE_KEY\n\n')
        f.write('# Create namespace\n')
        f.write('kubectl create namespace gloo-portal --dry-run=client -o yaml | kubectl apply -f -\n\n')
        f.write('# Deploy Portal resources\n')
        f.write(f'kubectl apply -f {output_dir}/\n\n')
        f.write('# Verify\n')
        f.write('echo ""\n')
        f.write('echo "Portals:"\n')
        f.write('kubectl get portals -n gloo-portal\n')
        f.write('echo ""\n')
        f.write('echo "API Products:"\n')
        f.write('kubectl get apiproducts -n gloo-portal\n')
    deploy_script.chmod(0o755)
    
    # Create README
    readme = output_path / 'README.md'
    with open(readme, 'w') as f:
        f.write('# Generated Gloo Portal Resources\n\n')
        f.write('## Summary\n\n')
        f.write(f'- **Portals:** {total_portals}\n')
        f.write(f'- **API Products:** {total_products}\n')
        f.write(f'- **Usage Plans:** {total_plans}\n\n')
        f.write('## Deployment\n\n')
        f.write('```bash\n')
        f.write('# Deploy all resources\n')
        f.write('./deploy.sh\n')
        f.write('```\n\n')
        f.write('## Verification\n\n')
        f.write('```bash\n')
        f.write('# Check Portals\n')
        f.write('kubectl get portals -n gloo-portal\n\n')
        f.write('# Check API Products\n')
        f.write('kubectl get apiproducts -n gloo-portal\n\n')
        f.write('# Get Portal URL\n')
        for catalog in mapping.get('catalogs', []):
            portal_name = catalog['portal_name']
            f.write(f'kubectl get portal {portal_name} -n gloo-portal -o jsonpath="{{.status.portalUrl}}"\n')
        f.write('```\n')
    
    print("=" * 70)
    print("  Summary")
    print("=" * 70)
    print(f'✅ Portals created: {total_portals}')
    print(f'✅ API Products created: {total_products}')
    print(f'✅ Usage Plans created: {total_plans}')
    print(f'📁 Output directory: {output_path.absolute()}')
    print()
    print('Next steps:')
    print(f'   1. Review generated YAML files in {output_dir}/')
    print(f'   2. Run: cd {output_dir} && ./deploy.sh')
    print(f'   3. Create APIDoc resources for each API (see CATALOG_TO_PORTAL_MIGRATION.md)')
    print(f'   4. Access portals at configured domains')
    print()


def create_sample_mapping():
    """Create a sample catalog-mapping.yaml file"""
    sample = {
        'catalogs': [
            {
                'name': 'production',
                'portal_name': 'production-portal',
                'description': 'Production APIs for external partners',
                'domains': ['portal.company.com'],
                'branding': {
                    'logo_url': 'https://company.com/logo.png',
                    'primary_color': '#0033A0'
                },
                'collections': [
                    {
                        'name': 'Customer APIs',
                        'product_name': 'customer-apis',
                        'description': 'APIs for customer management',
                        'apis': [
                            'customer-preferences-api',
                            'customer-profile-api'
                        ],
                        'plans': [
                            {
                                'name': 'Gold',
                                'rate_limit': '10000/day',
                                'auth_type': 'apiKey'
                            },
                            {
                                'name': 'Silver',
                                'rate_limit': '1000/day',
                                'auth_type': 'apiKey'
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    with open('catalog-mapping-sample.yaml', 'w') as f:
        yaml.dump(sample, f, default_flow_style=False, sort_keys=False)
    
    print('✅ Created sample: catalog-mapping-sample.yaml')
    print('   Edit this file with your APIC catalog structure')


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--create-sample':
        create_sample_mapping()
        sys.exit(0)
    
    if len(sys.argv) != 3:
        print('Usage:')
        print('  python migrate_catalog_to_portal.py <catalog-mapping.yaml> <output-dir>')
        print('  python migrate_catalog_to_portal.py --create-sample')
        print()
        print('Example:')
        print('  python migrate_catalog_to_portal.py catalog-mapping.yaml ./portal-configs')
        sys.exit(1)
    
    migrate_catalog_to_portal(sys.argv[1], sys.argv[2])
