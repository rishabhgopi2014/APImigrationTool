"""
Configuration Loader Module

Loads and validates developer configuration with multi-tenant support.
Handles environment variable substitution and secret management.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class OwnerConfig(BaseModel):
    """API ownership metadata"""
    team: str = Field(..., pattern=r"^[a-z0-9-]+$")
    domain: str = Field(..., pattern=r"^[a-z0-9-]+$")
    contact: Optional[str] = None
    component: Optional[str] = None


class PlatformCredentials(BaseModel):
    """Platform-specific credentials"""
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""
    max_requests_per_second: int = 10


class PlatformDiscoveryConfig(BaseModel):
    """Discovery configuration for a platform"""
    enabled: bool = False
    credentials: Optional[PlatformCredentials] = None
    filters: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)


class KafkaCredentials(BaseModel):
    """Kafka-specific credentials"""
    bootstrap_servers: list[str] = Field(default_factory=list)
    security_protocol: str = "PLAINTEXT"


class KafkaDiscoveryConfig(BaseModel):
    """Kafka discovery configuration"""
    enabled: bool = False
    credentials: Optional[KafkaCredentials] = None
    topics: list[str] = Field(default_factory=list)
    consumer_groups: list[str] = Field(default_factory=list)


class DiscoveryConfig(BaseModel):
    """Discovery configuration for all platforms"""
    apic: Optional[PlatformDiscoveryConfig] = None
    mulesoft: Optional[PlatformDiscoveryConfig] = None
    kafka: Optional[KafkaDiscoveryConfig] = None
    swagger: Optional[PlatformDiscoveryConfig] = None


class GlooGatewayConfig(BaseModel):
    """Gloo Gateway configuration"""
    namespace: str = "gloo-system"
    cluster: Optional[str] = None


class GlooPortalConfig(BaseModel):
    """Gloo Portal configuration"""
    url: Optional[str] = None


class GlooConfig(BaseModel):
    """Gloo platform configuration"""
    gateway: GlooGatewayConfig
    portal: Optional[GlooPortalConfig] = None


class TrafficShiftingConfig(BaseModel):
    """Traffic shifting configuration"""
    phases: list[int] = Field(default=[5, 25, 50, 100])
    approval_required: bool = True

    @field_validator('phases')
    @classmethod
    def validate_phases(cls, v):
        """Validate traffic shift phases"""
        if not all(0 <= phase <= 100 for phase in v):
            raise ValueError("All phases must be between 0 and 100")
        if sorted(v) != v:
            raise ValueError("Phases must be in ascending order")
        return v


class RollbackConfig(BaseModel):
    """Automatic rollback configuration"""
    error_threshold: float = Field(default=0.05, ge=0.0, le=1.0)
    latency_threshold_ms: int = Field(default=2000, gt=0)


class MigrationConfig(BaseModel):
    """Migration execution settings"""
    traffic_shifting: TrafficShiftingConfig = Field(default_factory=TrafficShiftingConfig)
    rollback: RollbackConfig = Field(default_factory=RollbackConfig)


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = "postgresql://localhost:5432/api_migration"


class RedisConfig(BaseModel):
    """Redis configuration"""
    url: str = "redis://localhost:6379/0"


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    format: str = "json"
    correlation_id: bool = True


class SlackNotificationConfig(BaseModel):
    """Slack notification configuration"""
    webhook_url: Optional[str] = None
    channel: Optional[str] = None


class EmailNotificationConfig(BaseModel):
    """Email notification configuration"""
    smtp_server: Optional[str] = None
    from_address: Optional[str] = Field(None, alias="from")
    to_addresses: list[str] = Field(default_factory=list, alias="to")


class NotificationConfig(BaseModel):
    """Notification configuration"""
    slack: Optional[SlackNotificationConfig] = None
    email: Optional[EmailNotificationConfig] = None


class Config(BaseModel):
    """Main configuration"""
    owner: OwnerConfig
    discovery: DiscoveryConfig
    gloo: GlooConfig
    migration: MigrationConfig = Field(default_factory=MigrationConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    notifications: Optional[NotificationConfig] = None


class ConfigLoader:
    """
    Configuration loader with environment variable substitution
    and validation.
    """

    ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')

    @staticmethod
    def _substitute_env_vars(value: Any) -> Any:
        """
        Recursively substitute environment variables in configuration values.
        
        Supports ${VAR_NAME} syntax.
        """
        if isinstance(value, str):
            def replace_env_var(match):
                var_name = match.group(1)
                env_value = os.getenv(var_name)
                if env_value is None:
                    raise ValueError(
                        f"Environment variable {var_name} is not set but required in config"
                    )
                return env_value
            
            return ConfigLoader.ENV_VAR_PATTERN.sub(replace_env_var, value)
        
        elif isinstance(value, dict):
            return {k: ConfigLoader._substitute_env_vars(v) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [ConfigLoader._substitute_env_vars(item) for item in value]
        
        return value

    @staticmethod
    def load(config_path: str = "config.yaml") -> Config:
        """
        Load and validate configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Validated Config object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Copy config.example.yaml to config.yaml and customize for your team."
            )
        
        # Load YAML
        with open(config_file) as f:
            raw_config = yaml.safe_load(f)
        
        # Substitute environment variables
        processed_config = ConfigLoader._substitute_env_vars(raw_config)
        
        # Validate with Pydantic
        try:
            config = Config(**processed_config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")
        
        return config

    @staticmethod
    def validate_file(config_path: str = "config.yaml") -> tuple[bool, Optional[str]]:
        """
        Validate configuration file without loading.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ConfigLoader.load(config_path)
            return True, None
        except Exception as e:
            return False, str(e)
