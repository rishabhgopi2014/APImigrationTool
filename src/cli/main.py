"""
CLI Main Entry Point

Command-line interface for API migration orchestrator.
Provides commands for discovery, planning, deployment, traffic management, and more.
"""

import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from ..config import ConfigLoader
from ..ownership import OwnershipManager
from ..state import LockManager, StateTracker, MigrationStatus
from ..connectors import APICConnector, SwaggerConnector
from ..discovery import BatchProcessor
from ..config.filter_engine import PlatformFilterEngine
from ..audit import AuditLogger

console = Console()


@click.group()
@click.option('--config', default='config.yaml', help='Path to configuration file')
@click.pass_context
def cli(ctx, config):
    """
    API Migration Orchestrator CLI
    
    Migrate APIs from legacy platforms (APIC, MuleSoft, Kafka, Swagger) 
    to Gloo Gateway and Portal with zero downtime.
    """
    # Load configuration
    try:
        ctx.obj = {'config_path': config}
        ctx.obj['config'] = ConfigLoader.load(config)
        console.print(f"✓ Loaded configuration from {config}", style="green")
    except FileNotFoundError:
        console.print(f"✗ Configuration file not found: {config}", style="red")
        console.print("  Copy config.example.yaml to config.yaml and customize for your team")
        ctx.exit(1)
    except Exception as e:
        console.print(f"✗ Invalid configuration: {e}", style="red")
        ctx.exit(1)


@cli.command()
@click.option('--platform', help='Discover from specific platform only')
@click.option('--no-cache', is_flag=True, help='Ignore cached results')
@click.option('--show-all', is_flag=True, help='Show all discovered APIs (not just first 50)')
@click.pass_context
def discover(ctx, platform, no_cache, show_all):
    """
    Discover APIs from configured platforms with traffic analysis.
    
    Analyzes traffic patterns and calculates risk scores to help prioritize migrations.
    """
    config = ctx.obj['config']
    
    console.print("\n🔍 API Discovery & Risk Analysis", style="bold blue")
    console.print(f"Team: {config.owner.team}")
    console.print(f"Domain: {config.owner.domain}\n")
    
    # Initialize connectors based on enabled platforms
    connectors = {}
    
    if config.discovery.apic and config.discovery.apic.enabled:
        if platform is None or platform == 'apic':
            console.print("📡 APIC discovery enabled", style="cyan")
            connectors['apic'] = APICConnector(
                credentials=config.discovery.apic.credentials.dict() if config.discovery.apic.credentials else {},
                rate_limit=config.discovery.apic.rate_limit.max_requests_per_second
            )
    
    if config.discovery.swagger and config.discovery.swagger.enabled:
        if platform is None or platform == 'swagger':
            console.print("📡 Swagger discovery enabled", style="cyan")
            connectors['swagger'] = SwaggerConnector(
                credentials=config.discovery.swagger.credentials.dict() if config.discovery.swagger.credentials else {},
                rate_limit=config.discovery.swagger.rate_limit.max_requests_per_second
            )
    
    if not connectors:
        console.print("✗ No platforms enabled for discovery", style="red")
        console.print("  Enable platforms in your config.yaml")
        return
    
    # Create filter engines per platform
    from ..config.filter_engine import FilterEngine
    
    filter_engines = {}
    for platform_name in connectors.keys():
        platform_config = getattr(config.discovery, platform_name, None)
        if platform_config:
            filter_engines[platform_name] = FilterEngine(
                include_patterns=platform_config.filters,
                exclude_patterns=platform_config.exclude_patterns,
                tags=platform_config.tags,
                owner_team=config.owner.team,
                owner_domain=config.owner.domain
            )
    
    # Run batch discovery
    batch_processor = BatchProcessor(
        connectors=connectors,
        filter_engine=filter_engines.get(list(connectors.keys())[0]) if filter_engines else None
    )
    
    results = batch_processor.discover_all(
        show_progress=True,
        use_cache=not no_cache
    )
    
    # Calculate risk scores for discovered APIs
    from ..inventory import RiskScorer, TrafficPattern, BusinessCriticality
    
    all_apis = batch_processor.get_all_apis(results)
    
    if all_apis:
        console.print("\n📊 Analyzing traffic patterns and calculating risk scores...", style="cyan")
        
        # Calculate risk for each API
        scorer = RiskScorer()
        api_risks = []
        
        for api in all_apis:
            # Create traffic pattern from API metadata
            traffic_pattern = TrafficPattern(
                avg_requests_per_day=api.avg_requests_per_day,
                avg_latency_ms=api.avg_latency_ms,
                error_rate=api.error_rate
            )
            
            # Calculate risk
            risk_score = scorer.calculate_risk(
                api_name=api.name,
                traffic_pattern=traffic_pattern,
                auth_methods=api.auth_methods,
                business_criticality=BusinessCriticality.MEDIUM  # Default
            )
            
            api_risks.append({
                "api": api,
                "risk": risk_score
            })
        
        # Sort by risk score (highest first)
        api_risks.sort(key=lambda x: x["risk"].overall_score, reverse=True)
        
        # Display comprehensive table
        table = Table(title=f"\n✨ Discovered APIs for {config.owner.team} (Sorted by Risk)")
        table.add_column("API Name", style="cyan", no_wrap=True)
        table.add_column("Platform", style="magenta")
        table.add_column("Traffic\n(req/day)", justify="right")
        table.add_column("Error\nRate", justify="right")
        table.add_column("Latency\n(ms)", justify="right")
        table.add_column("Risk\nScore", justify="center")
        table.add_column("Risk\nLevel", justify="center")
        table.add_column("Auth", style="yellow")
        
        # Risk level colors
        risk_colors = {
            "CRITICAL": "red bold",
            "HIGH": "red",
            "MEDIUM": "yellow",
            "LOW": "green"
        }
        
        display_count = len(api_risks) if show_all else min(50, len(api_risks))
        
        for item in api_risks[:display_count]:
            api = item["api"]
            risk = item["risk"]
            
            # Format traffic
            traffic_str = (
                f"{api.avg_requests_per_day:,}" 
                if api.avg_requests_per_day 
                else "Unknown"
            )
            
            # Format error rate
            error_str = (
                f"{api.error_rate*100:.2f}%" 
                if api.error_rate is not None 
                else "Unknown"
            )
            
            # Format latency
            latency_str = (
                f"{api.avg_latency_ms}" 
                if api.avg_latency_ms 
                else "Unknown"
            )
            
            # Format auth
            auth_str = ", ".join(api.auth_methods[:2]) if api.auth_methods else "None"
            
            table.add_row(
                api.name[:40],  # Truncate long names
                api.platform,
                traffic_str,
                error_str,
                latency_str,
                f"{risk.overall_score:.2f}",
                f"[{risk_colors[risk.risk_level.value]}]{risk.risk_level.value}[/]",
                auth_str[:15]
            )
        
        console.print(table)
        
        if len(api_risks) > display_count:
            console.print(f"\n... and {len(api_risks) - display_count} more APIs (use --show-all to see all)")
        
        # Risk distribution summary
        risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for item in api_risks:
            risk_counts[item["risk"].risk_level.value] += 1
        
        console.print(f"\n📊 Risk Distribution:")
        console.print(f"   [red bold]CRITICAL[/]: {risk_counts['CRITICAL']} APIs")
        console.print(f"   [red]HIGH[/]: {risk_counts['HIGH']} APIs")
        console.print(f"   [yellow]MEDIUM[/]: {risk_counts['MEDIUM']} APIs")
        console.print(f"   [green]LOW[/]: {risk_counts['LOW']} APIs")
        
        console.print(f"\n✓ Total APIs discovered: {len(all_apis)}", style="bold green")
        
        # Migration priority recommendations
        console.print(f"\n💡 Migration Strategy:")
        console.print(f"   • Start with [green]LOW[/] risk APIs to build confidence")
        console.print(f"   • Migrate [red]CRITICAL[/] APIs last with extensive testing")
        console.print(f"   • Consider migrating APIs with similar traffic patterns together")
    else:
        console.print("\n⚠ No APIs matched your filters", style="yellow")
    
    # Show statistics
    stats = batch_processor.get_statistics(results)
    console.print(f"\n📊 Discovery Statistics:")
    console.print(f"   Platforms queried: {stats['total_platforms']}")
    console.print(f"   Successful: {stats['successful_platforms']}")
    console.print(f"   Total discovered: {stats['total_discovered']}")
    console.print(f"   After filtering: {stats['total_filtered']}")
    console.print(f"   Filter reduction: {stats['filter_reduction_pct']:.1f}%")
    console.print(f"   Duration: {stats['total_duration_seconds']:.1f}s\n")


@cli.command()
@click.option('--domain', help='Filter by domain')
@click.option('--platform', help='Filter by platform')
@click.option('--risk', type=click.Choice(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']), help='Filter by risk level')
@click.pass_context
def list(ctx, domain, platform, risk):
    """
    List discovered APIs in your domain.
    
    Shows APIs from the inventory database.
    """
    config = ctx.obj['config']
    
    console.print("\n📋 API Inventory", style="bold blue")
    console.print(f"Team: {config.owner.team}\n")
    
    # TODO: Query database for APIs
    console.print("⚠ Database integration pending - use 'discover' command first", style="yellow")


@cli.command()
@click.argument('api_name')
@click.option('--platform', default='apic', help='Platform name')
@click.pass_context
def plan(ctx, api_name, platform):
    """
    Generate migration plan for an API.
    
    Creates Gloo Gateway configuration files.
    """
    config = ctx.obj['config']
    
    console.print(f"\n📝 Generating migration plan for {api_name}", style="bold blue")
    console.print(f"Platform: {platform}\n")
    
    # TODO: Implement plan generation
    console.print("⚠ Plan generation not yet implemented", style="yellow")


@cli.command()
@click.pass_context
def status(ctx):
    """
    Show migration status for your APIs.
    
    Displays current state of all APIs in migration.
    """
    config = ctx.obj['config']
    
    console.print(f"\n📊 Migration Status - {config.owner.team}", style="bold blue")
    
    # TODO: Query migration_state table
    console.print("\n⚠ Database integration pending", style="yellow")


@cli.command()
@click.pass_context
def locks(ctx):
    """
    Show active locks for API migrations.
    
    Displays which APIs are currently locked and by whom.
    """
    config = ctx.obj['config']
    
    console.print("\n🔒 Active Migration Locks", style="bold blue")
    
    # Initialize lock manager
    lock_manager = LockManager(
        redis_url=config.redis.url,
        team_name=config.owner.team
    )
    
    active_locks = lock_manager.list_active_locks()
    
    if active_locks:
        table = Table(title="Active Locks")
        table.add_column("API Name", style="cyan")
        table.add_column("Platform", style="magenta")
        table.add_column("Locked By", style="yellow")
        table.add_column("Locked At", style="green")
        table.add_column("Expires At", style="red")
        
        for lock in active_locks:
            table.add_row(
                lock.get('api_name', 'N/A'),
                lock.get('platform', 'N/A'),
                lock.get('team', 'N/A'),
                lock.get('locked_at', 'N/A'),
                lock.get('expires_at', 'N/A')
            )
        
        console.print(table)
    else:
        console.print("\n✓ No active locks", style="green")


@cli.command()
@click.pass_context
def validate_config(ctx):
    """
    Validate configuration file.
    
    Checks config.yaml for errors and shows loaded settings.
    """
    config_path = ctx.obj['config_path']
    
    console.print("\n🔍 Validating Configuration", style="bold blue")
    console.print(f"File: {config_path}\n")
    
    is_valid, error = ConfigLoader.validate_file(config_path)
    
    if is_valid:
        config = ctx.obj['config']
        
        console.print("✓ Configuration is valid!", style="bold green")
        console.print(f"\nOwner:")
        console.print(f"  Team: {config.owner.team}")
        console.print(f"  Domain: {config.owner.domain}")
        console.print(f"  Contact: {config.owner.contact}")
        
        console.print(f"\nDiscovery:")
        console.print(f"  APIC: {'enabled' if config.discovery.apic and config.discovery.apic.enabled else 'disabled'}")
        console.print(f"  MuleSoft: {'enabled' if config.discovery.mulesoft and config.discovery.mulesoft.enabled else 'disabled'}")
        console.print(f"  Kafka: {'enabled' if config.discovery.kafka and config.discovery.kafka.enabled else 'disabled'}")
        console.print(f"  Swagger: {'enabled' if config.discovery.swagger and config.discovery.swagger.enabled else 'disabled'}")
    else:
        console.print(f"✗ Configuration is invalid:", style="bold red")
        console.print(f"  {error}", style="red")


if __name__ == '__main__':
    cli(obj={})
