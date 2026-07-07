from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ProductConfig(BaseModel):
    url: str
    size_or_variant: str = ""
    max_price: float = 0.0
    quantity: int = 1


class MonitorConfig(BaseModel):
    poll_interval_seconds: int = 5
    jitter_seconds: int = 2


class CheckoutConfig(BaseModel):
    mode: str = "auto"
    timeout_seconds: int = 30
    retry_attempts: int = 3


class ProfileConfig(BaseModel):
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    address1: str = ""
    address2: str = ""
    city: str = ""
    province: str = ""
    zip: str = ""
    country: str = "US"
    phone: str = ""


class PaymentConfig(BaseModel):
    card_number: str = ""
    card_name: str = ""
    card_expiry_month: str = ""
    card_expiry_year: str = ""
    card_cvv: str = ""


class ProxyConfig(BaseModel):
    enabled: bool = False
    rotation: str = "round_robin"
    file: str = "config/proxies.txt"


class CaptchaConfig(BaseModel):
    enabled: bool = False
    provider: str = "2captcha"
    api_key: str = ""


class DiscordNotifConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""


class NotificationsConfig(BaseModel):
    discord: DiscordNotifConfig = Field(default_factory=DiscordNotifConfig)
    console: dict = Field(default_factory=lambda: {"enabled": True})


class BrowserConfig(BaseModel):
    headless: bool = True
    user_agent: str = ""


class Settings(BaseModel):
    products: list[ProductConfig] = Field(default_factory=list)
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)
    checkout: CheckoutConfig = Field(default_factory=CheckoutConfig)
    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    payment: PaymentConfig = Field(default_factory=PaymentConfig)
    proxies: ProxyConfig = Field(default_factory=ProxyConfig)
    captcha: CaptchaConfig = Field(default_factory=CaptchaConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)


def load_settings(path: str = "config/settings.yaml") -> Settings:
    config_path = Path(path)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        print("Copy config/settings.example.yaml to config/settings.yaml and fill in your values.")
        sys.exit(1)

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    return Settings.model_validate(raw or {})
