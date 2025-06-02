import json
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field, model_validator


class RedditConfig(BaseModel):
    """Configuration for KarmaLord with validation"""

    # Rate limiting (CRITICAL for avoiding detection)
    min_delay_between_actions: float = Field(
        default=8.0,
        ge=3.0,
        le=60.0,
        description="Minimum delay between actions (seconds)",
    )
    max_delay_between_actions: float = Field(
        default=25.0,
        ge=5.0,
        le=120.0,
        description="Maximum delay between actions (seconds)",
    )
    min_delay_between_accounts: float = Field(
        default=45.0,
        ge=10.0,
        le=300.0,
        description="Minimum delay between account switches (seconds)",
    )
    max_delay_between_accounts: float = Field(
        default=180.0,
        ge=30.0,
        le=600.0,
        description="Maximum delay between account switches (seconds)",
    )
    min_delay_between_targets: float = Field(
        default=30.0,
        ge=5.0,
        le=300.0,
        description="Minimum delay between target users (seconds)",
    )
    max_delay_between_targets: float = Field(
        default=90.0,
        ge=10.0,
        le=600.0,
        description="Maximum delay between target users (seconds)",
    )

    # Safety limits
    max_actions_per_hour: int = Field(
        default=8, ge=1, le=20, description="Maximum actions per hour per account"
    )
    max_actions_per_day: int = Field(
        default=35, ge=5, le=100, description="Maximum actions per day per account"
    )

    # Network parameters
    request_timeout: int = Field(
        default=45, ge=10, le=120, description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3, ge=1, le=10, description="Maximum request retries"
    )
    backoff_factor: float = Field(
        default=2.5, ge=1.0, le=5.0, description="Backoff factor for retries"
    )

    # Stealth features
    rotate_tls_profiles: bool = Field(
        default=True, description="Rotate TLS fingerprints periodically"
    )
    browser_rotation_hours: int = Field(
        default=2, ge=1, le=24, description="Hours between browser rotation"
    )

    # Tracking system
    check_interval: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Check interval for new posts (seconds)",
    )
    max_post_age_hours: int = Field(
        default=48, ge=1, le=168, description="Maximum age of posts to process (hours)"
    )

    # Proxy settings (optional)
    use_proxy_rotation: bool = Field(default=False, description="Enable proxy rotation")
    proxy_list: List[str] = Field(
        default_factory=list, description="List of proxy URLs (http://ip:port)"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )
    log_file: str = Field(default="karmalord.log", description="Log file path")
    save_session_data: bool = Field(
        default=True, description="Save session data for persistence"
    )

    # File paths
    accounts_file: str = Field(
        default="accounts.json", description="Path to accounts configuration file"
    )
    targets_file: str = Field(
        default="targets.json", description="Path to targets configuration file"
    )
    session_data_file: str = Field(
        default="session_data.json", description="Path to session data file"
    )

    # Discord webhook notifications
    discord_webhook_enabled: bool = Field(
        default=False, description="Enable Discord webhook notifications"
    )
    discord_webhook_url: str = Field(
        default="", description="Discord webhook URL for notifications"
    )
    discord_notify_on_action: bool = Field(
        default=True, description="Send notification for each vote action"
    )
    discord_notify_on_cycle_complete: bool = Field(
        default=True, description="Send notification when a check cycle completes"
    )
    discord_notify_on_errors: bool = Field(
        default=True, description="Send notification when errors occur"
    )

    @model_validator(mode="after")
    def validate_delays_and_limits(self):
        """Validate that max values are greater than min values"""
        # Validate delay between actions
        if self.max_delay_between_actions <= self.min_delay_between_actions:
            raise ValueError(
                "max_delay_between_actions must be greater than min_delay_between_actions"
            )

        # Validate delay between accounts
        if self.max_delay_between_accounts <= self.min_delay_between_accounts:
            raise ValueError(
                "max_delay_between_accounts must be greater than min_delay_between_accounts"
            )
        
        # Validate delay between targets
        if self.max_delay_between_targets <= self.min_delay_between_targets:
            raise ValueError(
                "max_delay_between_targets must be greater than min_delay_between_targets"
            )

        # Validate daily actions vs hourly actions
        if self.max_actions_per_day <= self.max_actions_per_hour:
            raise ValueError(
                "max_actions_per_day must be greater than max_actions_per_hour"
            )

        # Validate Discord webhook configuration
        if self.discord_webhook_enabled and not self.discord_webhook_url:
            raise ValueError(
                "discord_webhook_url must be provided when discord_webhook_enabled is True"
            )

        return self

    class Config:
        extra = "forbid"  # Don't allow extra fields
        validate_assignment = True  # Validate on assignment


def load_config(config_file: str = "config.json") -> RedditConfig:
    """Load configuration from JSON file with fallback to defaults"""
    config_path = Path(config_file)

    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)

            # Validate and create config
            config = RedditConfig(**config_data)
            print(f"✅ Configuration loaded from {config_file}")
            return config

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {config_file}: {e}")
            print("📄 Using default configuration")
            return RedditConfig()

        except Exception as e:
            print(f"❌ Error loading config from {config_file}: {e}")
            print("📄 Using default configuration")
            return RedditConfig()
    else:
        print(f"📄 Config file {config_file} not found, using defaults")
        return RedditConfig()


def save_default_config(config_file: str = "config.json") -> None:
    """Save default configuration to JSON file"""
    config = RedditConfig()
    config_dict = config.model_dump()

    with open(config_file, "w") as f:
        json.dump(config_dict, f, indent=4)
