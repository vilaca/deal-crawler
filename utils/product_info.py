"""Product information extraction utilities."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductInfo:
    """Product size and quantity information."""

    volume_ml: Optional[float] = None  # Volume per unit in ml
    quantity: int = 1  # Number of units
    total_volume_ml: Optional[float] = None  # Total volume (quantity * volume_ml)

    def __post_init__(self) -> None:
        """Calculate total volume after initialization."""
        if self.volume_ml is not None:
            self.total_volume_ml = self.volume_ml * self.quantity


def parse_product_name(product_name: str) -> ProductInfo:
    """Extract size and quantity information from product name.

    Supports patterns like:
    - (236ml) - single item with volume
    - (2x236ml) - multiple items with volume per unit
    - (1000ml) - single item with volume

    Args:
        product_name: Product name string

    Returns:
        ProductInfo with extracted volume and quantity
    """
    # Pattern for quantity + volume: (2x236ml), (3x100ml)
    multi_match = re.search(r"\((\d+)x(\d+(?:\.\d+)?)ml\)", product_name, re.IGNORECASE)
    if multi_match:
        quantity = int(multi_match.group(1))
        volume = float(multi_match.group(2))
        return ProductInfo(volume_ml=volume, quantity=quantity)

    # Pattern for single volume: (236ml), (1000ml)
    single_match = re.search(r"\((\d+(?:\.\d+)?)ml\)", product_name, re.IGNORECASE)
    if single_match:
        volume = float(single_match.group(1))
        return ProductInfo(volume_ml=volume, quantity=1)

    # No volume information found
    return ProductInfo()


def calculate_price_per_100ml(price: float, total_volume_ml: float) -> float:
    """Calculate price per 100ml.

    Args:
        price: Total price
        total_volume_ml: Total volume in ml

    Returns:
        Price per 100ml
    """
    return (price / total_volume_ml) * 100


def format_volume_info(product_info: ProductInfo) -> str:
    """Format volume information for display.

    Args:
        product_info: ProductInfo object

    Returns:
        Formatted string like "236ml" or "2x236ml (472ml total)"
    """
    if product_info.volume_ml is None:
        return ""

    if product_info.quantity == 1:
        return f"{product_info.volume_ml:.0f}ml"

    total = product_info.total_volume_ml or 0
    return f"{product_info.quantity}x{product_info.volume_ml:.0f}ml ({total:.0f}ml)"


def format_price_per_unit(price_per_100ml: float) -> str:
    """Format price per 100ml for display.

    Args:
        price_per_100ml: Price per 100ml

    Returns:
        Formatted string like "€3.10/100ml"
    """
    return f"€{price_per_100ml:.2f}/100ml"
