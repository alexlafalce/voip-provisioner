"""Configuration loader for the provisioning server."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"
    json_logs: bool = True


class PathsConfig(BaseModel):
    """File paths configuration."""

    inventory_dir: str = "inventory"
    templates_dir: str = "templates"
    secrets_file: str = "inventory/secrets.yml"


class PBXConfig(BaseModel):
    """PBX connection settings."""

    server: str = "pbx.example.com"
    port: int = 5060
    transport: str = "UDP"


class TimeConfig(BaseModel):
    """Time/NTP settings."""

    ntp_server: str = "pool.ntp.org"
    timezone: str = "America/New_York"


class VendorOUI(BaseModel):
    """MAC OUI prefixes for vendor detection."""

    yealink: list[str] = Field(default_factory=lambda: ["001565", "805E0C", "805EC0"])
    fanvil: list[str] = Field(default_factory=lambda: ["0C383E", "7C2F80"])
    grandstream: list[str] = Field(default_factory=lambda: ["000B82", "C074AD", "001631", "3C4005"])


class AsteriskConfig(BaseModel):
    """Asterisk AMI configuration."""

    enabled: bool = False
    host: str = "localhost"
    port: int = 5038
    username: str = "admin"
    password: str = "secret"
    timeout: int = 5

    # Config file paths (on Asterisk server or shared volume)
    pjsip_config_path: str = "/etc/asterisk/pjsip.conf"
    extensions_config_path: str = "/etc/asterisk/extensions.conf"

    # Generation settings
    context: str = "from-internal"
    transport: str = "transport-udp"

    # Error handling
    fail_on_ami_error: bool = False
    retry_on_failure: bool = True
    retry_max_attempts: int = 3
    retry_delay_seconds: int = 5


class Config(BaseSettings):
    """Main configuration container."""

    server: ServerConfig = Field(default_factory=ServerConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    pbx: PBXConfig = Field(default_factory=PBXConfig)
    time: TimeConfig = Field(default_factory=TimeConfig)
    vendor_oui: VendorOUI = Field(default_factory=VendorOUI)
    asterisk: AsteriskConfig = Field(default_factory=AsteriskConfig)

    # Base directory (set at runtime)
    base_dir: Path = Field(default_factory=lambda: Path.cwd())


def load_config(config_path: Path | str | None = None) -> Config:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config.yml. If None, looks in current directory.

    Returns:
        Populated Config object.
    """
    if config_path is None:
        config_path = Path.cwd() / "config.yml"
    else:
        config_path = Path(config_path)

    base_dir = config_path.parent

    config_data: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}

    config_data["base_dir"] = base_dir

    # Parse nested config sections
    config = Config(
        server=ServerConfig(**config_data.get("server", {})),
        paths=PathsConfig(**config_data.get("paths", {})),
        pbx=PBXConfig(**config_data.get("pbx", {})),
        time=TimeConfig(**config_data.get("time", {})),
        vendor_oui=VendorOUI(**config_data.get("vendor_oui", {})),
        asterisk=AsteriskConfig(**config_data.get("asterisk", {})),
        base_dir=base_dir,
    )

    return config


# Global config instance (populated on startup)
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
