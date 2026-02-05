#!/usr/bin/env python3
"""
Bulk Config Generator - Generate Gloo Gateway configs for multiple APIs

This script discovers all APIs and generates Kubernetes YAML configs for each one.
Useful for batch processing and preparing for mass migration.

Usage:
    python bulk_generate_configs.py --output-dir ./generated-configs
    python bulk_generate_configs.py --api-names "customer-api,payment-api" --output-dir ./configs
"""

import os
import sys
import argparse
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.connectors.apic_connector import APICConnector
from src.translator.gloo_generator import GlooConfigGenerator


def load_env():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value


def discover_apis():
    """Discover APIs from configured sources"""
    print("🔍 Discovering APIs...")
    
    # Load credentials from environment
    credentials = {
        "url": os.getenv("APIC_BASE_URL", ""),
        "username": os.getenv("APIC_USERNAME", ""),
        "password": os.getenv("APIC_PASSWORD", ""),
        "token": os.getenv("APIC_TOKEN", "")
    }
    
    # Create connector
    connector = APICConnector(credentials=credentials, rate_limit=10)
    
    # Discover APIs
    apis = connector.discover_apis()
    
    print(f"✅ Discovered {len(apis)} APIs")
    return apis


def generate_config_for_api(api, output_dir, namespace="gloo-system"):
    """Generate Gloo configs for a single API"""
    
    # Create output directory for this API
    api_dir = Path(output_dir) / api.name
    api_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📝 Generating configs for: {api.name}")
    print(f"   Platform: {api.platform}")
    print(f"   Base Path: {api.base_path}")
    print(f"   Auth: {', '.join(api.auth_methods) if api.auth_methods else 'None'}")
    
    # Generate Gloo configuration
    generator = GlooConfigGenerator(namespace=namespace)
    gloo_config = generator.generate(api, backend_host=None)
    
    # Get YAML files
    yaml_files = gloo_config.to_yaml_files()
    
    # Write each YAML to file
    files_written = []
    for filename, content in yaml_files.items():
        filepath = api_dir / filename
        with open(filepath, 'w') as f:
            f.write(content)
        files_written.append(filepath)
        print(f"   ✅ Created: {filepath}")
    
    # Create a README for this API
    readme_path = api_dir / "README.md"
    with open(readme_path, 'w') as f:
        f.write(f"# {api.name}\n\n")
        f.write(f"**Platform:** {api.platform}\n")
        f.write(f"**Base Path:** {api.base_path}\n")
        f.write(f"**Version:** {api.version}\n")
        f.write(f"**Description:** {api.description}\n\n")
        
        if api.auth_methods:
            f.write(f"**Authentication:** {', '.join(api.auth_methods)}\n\n")
        
        f.write("## Deployment\n\n")
        f.write("```bash\n")
        f.write("# Apply all configs for this API\n")
        f.write(f"kubectl apply -f {api_dir}/\n\n")
        f.write("# Or apply individually:\n")
        for filepath in files_written:
            f.write(f"kubectl apply -f {filepath.name}\n")
        f.write("```\n\n")
        
        f.write("## Verification\n\n")
        f.write("```bash\n")
        f.write(f"# Check VirtualService\n")
        f.write(f"kubectl get vs {api.name}-vs -n {namespace}\n\n")
        f.write(f"# Check Upstream\n")
        f.write(f"kubectl get upstream {api.name}-upstream -n {namespace}\n")
        f.write("```\n")
    
    print(f"   📄 Created: {readme_path}")
    
    return files_written


def create_summary(apis_processed, output_dir):
    """Create a summary README for all generated configs"""
    summary_path = Path(output_dir) / "SUMMARY.md"
    
    with open(summary_path, 'w') as f:
        f.write("# Generated Gloo Gateway Configurations\n\n")
        f.write(f"**Total APIs:** {len(apis_processed)}\n")
        f.write(f"**Generated:** {Path(output_dir).absolute()}\n\n")
        
        f.write("## APIs\n\n")
        f.write("| API Name | Platform | Base Path | Auth Methods | Files |\n")
        f.write("|----------|----------|-----------|--------------|-------|\n")
        
        for api_name, file_count in apis_processed.items():
            api_dir = Path(output_dir) / api_name
            f.write(f"| [{api_name}](./{api_name}/) | ")
            
            # Read the API's README to get details
            readme_path = api_dir / "README.md"
            if readme_path.exists():
                with open(readme_path) as readme:
                    content = readme.read()
                    # Extract platform, base_path, auth
                    platform = "Unknown"
                    base_path = "/"
                    auth = "None"
                    
                    for line in content.split('\n'):
                        if line.startswith("**Platform:**"):
                            platform = line.split("**Platform:**")[1].strip()
                        elif line.startswith("**Base Path:**"):
                            base_path = line.split("**Base Path:**")[1].strip()
                        elif line.startswith("**Authentication:**"):
                            auth = line.split("**Authentication:**")[1].strip()
                    
                    f.write(f"{platform} | {base_path} | {auth} | {file_count} |\n")
        
        f.write("\n## Bulk Deployment\n\n")
        f.write("### Deploy All APIs\n\n")
        f.write("```bash\n")
        f.write(f"# Deploy all at once (careful!)\n")
        f.write(f"kubectl apply -f {output_dir}/ -R\n")
        f.write("```\n\n")
        
        f.write("### Deploy Specific APIs\n\n")
        f.write("```bash\n")
        for api_name in sorted(apis_processed.keys()):
            f.write(f"kubectl apply -f {output_dir}/{api_name}/\n")
        f.write("```\n\n")
        
        f.write("## Verification\n\n")
        f.write("```bash\n")
        f.write("# Check all VirtualServices\n")
        f.write("kubectl get vs -n gloo-system\n\n")
        f.write("# Check all Upstreams\n")
        f.write("kubectl get upstream -n gloo-system\n\n")
        f.write("# Check all AuthConfigs\n")
        f.write("kubectl get authconfig -n gloo-system\n")
        f.write("```\n\n")
        
        f.write("## Next Steps\n\n")
        f.write("1. Review each API's generated configuration\n")
        f.write("2. Test in a staging environment first\n")
        f.write("3. Deploy low-risk APIs first\n")
        f.write("4. Monitor for 24-48 hours before next batch\n")
        f.write("5. See [KUBERNETES_DEPLOYMENT_GUIDE.md](../KUBERNETES_DEPLOYMENT_GUIDE.md) for detailed instructions\n")
    
    print(f"\n📊 Created summary: {summary_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Bulk generate Gloo Gateway configurations for multiple APIs"
    )
    parser.add_argument(
        '--output-dir',
        default='./generated-configs',
        help='Output directory for generated configs (default: ./generated-configs)'
    )
    parser.add_argument(
        '--namespace',
        default='gloo-system',
        help='Kubernetes namespace for Gloo resources (default: gloo-system)'
    )
    parser.add_argument(
        '--api-names',
        help='Comma-separated list of API names to generate (default: all)'
    )
    parser.add_argument(
        '--risk-level',
        choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
        help='Only generate configs for APIs with this risk level or lower'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("  Bulk Gloo Gateway Config Generator")
    print("=" * 70)
    print()
    
    # Load environment
    load_env()
    
    # Discover APIs
    all_apis = discover_apis()
    
    # Filter APIs if needed
    apis_to_process = all_apis
    
    if args.api_names:
        api_names_list = [name.strip() for name in args.api_names.split(',')]
        apis_to_process = [api for api in all_apis if api.name in api_names_list]
        print(f"\n🎯 Filtering to {len(apis_to_process)} specific APIs")
    
    if args.risk_level:
        risk_order = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        max_risk_index = risk_order.index(args.risk_level)
        apis_to_process = [
            api for api in apis_to_process
            if risk_order.index(api.risk_score.level) <= max_risk_index
        ]
        print(f"\n⚠️  Filtering to APIs with risk ≤ {args.risk_level}: {len(apis_to_process)} APIs")
    
    if not apis_to_process:
        print("❌ No APIs to process!")
        return 1
    
    print(f"\n🚀 Generating configs for {len(apis_to_process)} APIs...")
    print(f"   Output directory: {Path(args.output_dir).absolute()}")
    print(f"   Namespace: {args.namespace}")
    print()
    
    # Generate configs for each API
    apis_processed = {}
    successful = 0
    failed = 0
    
    for i, api in enumerate(apis_to_process, 1):
        try:
            print(f"[{i}/{len(apis_to_process)}]", end=" ")
            files = generate_config_for_api(api, args.output_dir, args.namespace)
            apis_processed[api.name] = len(files)
            successful += 1
        except Exception as e:
            print(f"\n❌ Failed to generate config for {api.name}: {e}")
            failed += 1
    
    # Create summary
    if apis_processed:
        create_summary(apis_processed, args.output_dir)
    
    # Print summary
    print("\n" + "=" * 70)
    print("  Summary")
    print("=" * 70)
    print(f"✅ Successful: {successful}")
    if failed:
        print(f"❌ Failed: {failed}")
    print(f"📁 Output Directory: {Path(args.output_dir).absolute()}")
    print()
    print("Next steps:")
    print(f"1. Review configs in: {args.output_dir}/")
    print(f"2. Read: {args.output_dir}/SUMMARY.md")
    print("3. Deploy to Kubernetes following KUBERNETES_DEPLOYMENT_GUIDE.md")
    print()
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
