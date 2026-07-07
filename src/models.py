from __future__ import annotations

import enum
from dataclasses import dataclass, field


class ProductStatus(enum.Enum):
    OUT_OF_STOCK = "out_of_stock"
    IN_STOCK = "in_stock"
    PREORDER = "preorder"
    UNKNOWN = "unknown"


class CheckoutResult(enum.Enum):
    SUCCESS = "success"
    SOLD_OUT = "sold_out"
    PAYMENT_FAILED = "payment_failed"
    CAPTCHA_FAILED = "captcha_failed"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ProductInfo:
    url: str
    title: str = ""
    price: float = 0.0
    status: ProductStatus = ProductStatus.UNKNOWN
    variant_id: str = ""
    image_url: str = ""


@dataclass
class CheckoutAttempt:
    product: ProductInfo
    result: CheckoutResult = CheckoutResult.ERROR
    order_number: str = ""
    message: str = ""
    duration_seconds: float = 0.0


@dataclass
class ProxyEntry:
    url: str
    failures: int = 0
    is_banned: bool = False


@dataclass
class AccountProfile:
    email: str
    first_name: str
    last_name: str
    address1: str
    address2: str = ""
    city: str = ""
    province: str = ""
    zip: str = ""
    country: str = "US"
    phone: str = ""


@dataclass
class PaymentInfo:
    card_number: str
    card_name: str
    card_expiry_month: str
    card_expiry_year: str
    card_cvv: str


@dataclass
class ProductTarget:
    url: str
    size_or_variant: str = ""
    max_price: float = 0.0
    quantity: int = 1
    keywords: list[str] = field(default_factory=list)
