from pydantic_settings import BaseSettings
from pydantic import field_validator

from .command_policy import parse_allowed_commands


class Settings(BaseSettings):
    """Application settings."""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # Command settings
    default_timeout: int = 60
    max_timeout: int = 300
    command_policy: str = "allowlist"
    # UNSAFE: bypass allowlist checks when True/False
    unsafe_allow_any_commands: bool = False
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Allowed commands (whitelist)
    allowed_commands: list[str] = [
        "Get-Process",
        "Get-Service", 
        "Get-EventLog",
        "Get-ComputerInfo",
        "Get-Volume",
        "Get-NetIPAddress",
        "Test-Connection",
        "whoami",
        "hostname",
        "ipconfig",
        "systeminfo",
        "Stop - Process",
    ]
    
    # Client settings
    client_heartbeat_interval: int = 30
    client_retry_attempts: int = 3
    client_retry_backoff_base: float = 2.0
    
    # UI settings
    template_dir: str = "templates"
    static_dir: str = "static"

    @field_validator("allowed_commands", mode="before")
    @classmethod
    def parse_allowed_commands_env(cls, value):
        return parse_allowed_commands(value)
    
    class Config:
        env_file = ".env"
        env_prefix = "RCD_"


# Global settings instance
settings = Settings()
