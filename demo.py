"""
API Migration Orchestrator - Demo Script

Demonstrates the complete flow:
1. Discovery from mock APIC
2. Risk scoring
3. Gloo Gateway config generation

Run: python demo.py
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import print as rprint
import yaml
import random

from src.connectors import APICConnector
from src.connectors.base import DiscoveredAPI
from src.config.filter_engine import FilterEngine
from src.inventory import RiskScorer, TrafficPattern, BusinessCriticality
from src.translator import GlooConfigGenerator

console = Console()


def generate_mock_apis():
    """Generate mock APIC APIs with catalog/collection structure"""
    
    # Catalog and collection structure
    catalog_structure = {
        "production": {
            "Customer Services": [
                ("customer-preferences-api", "Customer Preferences API", "/customer/v1/preferences", "Manage customer preferences and settings"),
                ("customer-profile-api", "Customer Profile API", "/customer/v1/profile", "Access and update customer profiles"),
                ("customer-loyalty-api", "Customer Loyalty API", "/loyalty/v1", "Loyalty points and rewards"),
            ],
            "Payment Services": [
                ("payment-gateway-api", "Payment Gateway API", "/payment/v1", "Process payments and transactions"),
                ("billing-api", "Billing API", "/billing/v1", "Invoice and billing"),
                ("refund-api", "Refund API", "/refund/v1", "Process refunds"),
            ],
            "Order Management": [
                ("order-api", "Order API", "/orders/v1", "Manage customer orders"),
                ("inventory-api", "Inventory API", "/inventory/v1", "Inventory tracking"),
                ("shipping-api", "Shipping API", "/shipping/v1", "Shipping services"),
            ],
        },
        "sandbox": {
            "Partner APIs": [
                ("partner-registration-api", "Partner Registration API", "/partner/v1/register", "Partner onboarding"),
                ("partner-reporting-api", "Partner Reporting API", "/partner/v1/reports", "Partner analytics"),
            ],
            "Internal Tools": [
                ("admin-api", "Admin API", "/admin/v1", "Internal administration"),
                ("monitoring-api", "Monitoring API", "/monitor/v1", "System monitoring"),
            ],
        }
    }
    
    apis = []
    
    for catalog_name, collections in catalog_structure.items():
        for collection_name, api_list in collections.items():
            for api_id, display_name, base_path, description in api_list:
                api = DiscoveredAPI(
                    name=api_id,
                    platform="apic",
                    base_path=base_path,
                    version="1.0.0",
                    description=description,
                    catalog=catalog_name,
                    collection=collection_name,
                    auth_methods=random.choice([["oauth"], ["api_key"], ["oauth", "api_key"], ["jwt"]]),
                    tags=["migrated", catalog_name, collection_name.lower().replace(" ", "-")],
                    owner_team=f"team-{collection_name.lower().replace(' ', '-')}",
                    owner_domain=collection_name.split()[0].lower(),
                    protocol="HTTP",
                    avg_requests_per_day=random.randint(1000, 100000),
                    avg_latency_ms=random.randint(50, 500),
                    error_rate=round(random.uniform(0.1, 5.0), 2),
                    legacy_metadata={
                        "apic_id": f"apic-{api_id}",
                        "catalog": catalog_name,
                        "collection": collection_name,
                        "display_name": display_name,
                        "backend_url": f"https://legacy-{api_id}.company.com:8443"
                    }
                )
                apis.append(api)
    
    return apis


def demo_discovery():
    """Demo API discovery with mock data"""
    console.print("\n" + "="*80, style="cyan")
    console.print("  🔍 STEP 1: API DISCOVERY FROM APIC (MOCK DATA)", style="bold cyan")
    console.print("="*80 + "\n", style="cyan")
    
    # Create APIC connector without credentials (triggers mock mode)
    # connector = APICConnector(credentials={}, rate_limit=10) # Original line
    
    # Simulate customer team discovering their APIs
    console.print("📡 Discovering APIs for [bold]customer-services[/bold] team...\n")
    
    # Apply filters to only get customer APIs
    # discovered_apis = connector.discover_apis(filters=["customer-*"]) # Original line
    
    # Use the new mock API generator
    all_mock_apis = generate_mock_apis()
    
    # Filter for customer-services team APIs
    filter_engine = FilterEngine(all_mock_apis)
    discovered_apis = filter_engine.filter_apis(
        filters=[
            {"field": "collection", "operator": "equals", "value": "Customer Services"},
            {"field": "catalog", "operator": "equals", "value": "production"}
        ]
    )
    
    console.print(f"✓ Discovered {len(discovered_apis)} APIs matching filter 'customer-*'\n")
    
    return discovered_apis


def demo_risk_scoring(apis):
    """Demo risk scoring"""
    console.print("\n" + "="*80, style="yellow")
    console.print("  📊 STEP 2: TRAFFIC ANALYSIS & RISK SCORING", style="bold yellow")
    console.print("="*80 + "\n", style="yellow")
    
    scorer = RiskScorer()
    api_risks = []
    
    for api in apis:
        traffic_pattern = TrafficPattern(
            avg_requests_per_day=api.avg_requests_per_day,
            avg_latency_ms=api.avg_latency_ms,
            error_rate=api.error_rate
        )
        
        risk_score = scorer.calculate_risk(
            api_name=api.name,
            traffic_pattern=traffic_pattern,
            auth_methods=api.auth_methods,
            business_criticality=BusinessCriticality.MEDIUM
        )
        
        api_risks.append({"api": api, "risk": risk_score})
    
    # Sort by risk (highest first)
    api_risks.sort(key=lambda x: x["risk"].overall_score, reverse=True)
    
    # Display table
    table = Table(title="Risk Analysis Results")
    table.add_column("API Name", style="cyan")
    table.add_column("Traffic\n(req/day)", justify="right")
    table.add_column("Error\nRate", justify="right")
    table.add_column("Latency\n(ms)", justify="right")
    table.add_column("Auth", style="yellow")
    table.add_column("Risk\nScore", justify="center")
    table.add_column("Risk\nLevel", justify="center")
    
    risk_colors = {
        "CRITICAL": "red bold",
        "HIGH": "red",
        "MEDIUM": "yellow",
        "LOW": "green"
    }
    
    for item in api_risks:
        api = item["api"]
        risk = item["risk"]
        
        table.add_row(
            api.name,
            f"{api.avg_requests_per_day:,}",
            f"{api.error_rate*100:.2f}%",
            f"{api.avg_latency_ms}",
            ", ".join(api.auth_methods[:2]) if api.auth_methods else "None",
            f"{risk.overall_score:.2f}",
            f"[{risk_colors[risk.risk_level.value]}]{risk.risk_level.value}[/]"
        )
    
    console.print(table)
    
    # Risk distribution
    risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for item in api_risks:
        risk_counts[item["risk"].risk_level.value] += 1
    
    console.print(f"\n📊 Risk Distribution:")
    console.print(f"   [red bold]CRITICAL[/]: {risk_counts['CRITICAL']} APIs")
    console.print(f"   [red]HIGH[/]: {risk_counts['HIGH']} APIs")
    console.print(f"   [yellow]MEDIUM[/]: {risk_counts['MEDIUM']} APIs")
    console.print(f"   [green]LOW[/]: {risk_counts['LOW']} APIs\n")
    
    return api_risks


def demo_gloo_translation(api_risks):
    """Demo APIC to Gloo Gateway translation"""
    console.print("\n" + "="*80, style="green")
    console.print("  ⚙️  STEP 3: APIC → GLOO GATEWAY TRANSLATION", style="bold green")
    console.print("="*80 + "\n", style="green")
    
    # Pick a low-risk API for demo (safest to migrate first)
    low_risk_apis = [item for item in api_risks if item["risk"].risk_level.value == "LOW"]
    
    if not low_risk_apis:
        # Fallback to lowest risk available
        demo_api_item = api_risks[-1]
    else:
        demo_api_item = low_risk_apis[0]
    
    demo_api = demo_api_item["api"]
    risk = demo_api_item["risk"]
    
    console.print(f"🎯 Generating Gloo Gateway config for: [bold cyan]{demo_api.name}[/bold cyan]")
    console.print(f"   Risk Level: [{risk.risk_level.value}] (Score: {risk.overall_score})")
    console.print(f"   Traffic: {demo_api.avg_requests_per_day:,} req/day")
    console.print(f"   Auth: {', '.join(demo_api.auth_methods) if demo_api.auth_methods else 'None'}\n")
    
    # Generate Gloo configs
    generator = GlooConfigGenerator(namespace="gloo-system")
    gloo_config = generator.generate(demo_api, backend_host="apic-gateway.company.com")
    
    # Show generated configs
    yaml_files = gloo_config.to_yaml_files()
    
    console.print("📄 Generated Kubernetes CRDs:\n")
    
    for filename, content in yaml_files.items():
        console.print(f"[bold]File: {filename}[/bold]")
        
        # Syntax highlight YAML
        syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=filename, border_style="green"))
        console.print("")
    
    # Show migration recommendations
    console.print("\n💡 Migration Recommendations:")
    for rec in risk.recommendations:
        console.print(f"   • {rec}")
    
    return gloo_config


def main():
    """Run complete demo"""
    console.print("\n" + "🚀 "*40, style="bold blue")
    console.print(" "*15 + "API MIGRATION ORCHESTRATOR - DEMO", style="bold blue")
    console.print("🚀 "*40 + "\n", style="bold blue")
    
    console.print(Panel.fit(
        "[bold]This demo shows:[/bold]\n"
        "1. Discovery of APIs from APIC (using mock data)\n"
        "2. Automatic traffic analysis and risk scoring\n"
        "3. Generation of Gloo Gateway Kubernetes configs\n\n"
        "[dim]No real APIC connection needed - using realistic mock data[/dim]",
        title="Demo Overview",
        border_style="blue"
    ))
    
    # Step 1: Discovery
    apis = demo_discovery()
    
    # Step 2: Risk scoring
    api_risks = demo_risk_scoring(apis)
    
    # Step 3: Gloo translation
    gloo_config = demo_gloo_translation(api_risks)
    
    # Summary
    console.print("\n" + "="*80, style="bold magenta")
    console.print("  ✨ DEMO COMPLETE!", style="bold magenta")
    console.print("="*80 + "\n", style="bold magenta")
    
    console.print("📋 Summary:")
    console.print(f"   • Discovered {len(apis)} APIs from APIC")
    console.print(f"   • Analyzed traffic patterns and calculated risk scores")
    console.print(f"   • Generated Gloo Gateway configs (VirtualService, Upstream, AuthConfig)")
    console.print(f"\n💡 Next Steps:")
    console.print(f"   1. Review generated configs in demo output above")
    console.print(f"   2. Start with LOW risk APIs for real migration")
    console.print(f"   3. Apply configs to Kubernetes: kubectl apply -f virtualservice.yaml")
    console.print(f"   4. Use traffic mirroring before full cutover\n")


if __name__ == "__main__":
    main()
