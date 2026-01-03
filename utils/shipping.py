"""Shipping configuration management."""

import sys
from dataclasses import dataclass, field
from typing import Dict
from urllib.parse import urlparse

import yaml


@dataclass
class ShippingInfo:
    """Shipping configuration for a single store."""

    site: str  # Domain (e.g., "aveirofarma.pt")
    shipping_cost: float  # Flat shipping cost in euros
    free_over: float  # Free shipping threshold in euros


@dataclass
class ShippingConfig:
    """Collection of shipping information for all stores."""

    stores: Dict[str, ShippingInfo] = field(default_factory=dict)  # site -> ShippingInfo
    default_shipping: float = 3.99  # Default shipping cost for unknown stores


def load_shipping_config(filepath: str) -> ShippingConfig:
    """Load shipping configuration from YAML file.

    Args:
        filepath: Path to shipping.yaml file

    Returns:
        ShippingConfig object with store shipping information

    Raises:
        FileNotFoundError: If shipping file doesn't exist
        yaml.YAMLError: If YAML is malformed
        ValueError: If shipping data is invalid
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError as e:
        print(f"\nError: Shipping file not found: {filepath}", file=sys.stderr)
        raise e
    except yaml.YAMLError as e:
        print(f"\nError: Invalid YAML in shipping file: {e}", file=sys.stderr)
        raise e

    if not isinstance(data, list):
        raise ValueError(f"Shipping file must contain a list, got {type(data)}")

    config = ShippingConfig()

    for item in data:
        if not isinstance(item, dict):
            print(f"\nWarning: Skipping invalid shipping entry: {item}", file=sys.stderr)
            continue

        # Validate required fields
        if "site" not in item or "shipping" not in item or "free-over" not in item:
            print(
                f"\nWarning: Skipping incomplete shipping entry (missing site, shipping, or free-over): {item}",
                file=sys.stderr,
            )
            continue

        try:
            site = str(item["site"]).strip()
            shipping_cost = float(item["shipping"])
            free_over = float(item["free-over"])

            # Normalize site domain (remove www. prefix for consistency)
            normalized_site = site.replace("www.", "")

            # Store with both original and normalized keys for flexibility
            shipping_info = ShippingInfo(site=site, shipping_cost=shipping_cost, free_over=free_over)
            config.stores[site] = shipping_info
            if normalized_site != site:
                config.stores[normalized_site] = shipping_info

        except (ValueError, TypeError) as e:
            print(f"\nWarning: Skipping invalid shipping entry: {item} - {e}", file=sys.stderr)
            continue

    if not config.stores:
        raise ValueError("No valid shipping information found in file")

    return config


def get_shipping_cost(subtotal: float, shipping_info: ShippingInfo) -> float:
    """Calculate shipping cost based on subtotal and store shipping rules.

    Args:
        subtotal: Order subtotal in euros
        shipping_info: Store shipping configuration

    Returns:
        Shipping cost in euros (0.0 if free shipping applies)
    """
    if subtotal >= shipping_info.free_over:
        return 0.0
    return shipping_info.shipping_cost


def get_shipping_info_for_url(url: str, config: ShippingConfig) -> ShippingInfo:
    """Get shipping info for a given product URL.

    Args:
        url: Product URL
        config: Shipping configuration

    Returns:
        ShippingInfo for the store, or default if not found
    """
    parsed = urlparse(url)
    domain = parsed.netloc

    # Try with full domain
    if domain in config.stores:
        return config.stores[domain]

    # Try without www. prefix
    domain_no_www = domain.replace("www.", "")
    if domain_no_www in config.stores:
        return config.stores[domain_no_www]

    # Return default
    print(f"\nWarning: No shipping info found for {domain}, using default €{config.default_shipping:.2f}", file=sys.stderr)
    return ShippingInfo(site=domain, shipping_cost=config.default_shipping, free_over=999.99)
