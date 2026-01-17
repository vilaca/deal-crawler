"""Shipping configuration and cost calculation."""

from dataclasses import dataclass
from typing import Dict

import yaml

# Constant representing no free shipping available (threshold unreachably high)
NO_FREE_SHIPPING_THRESHOLD = 999999.99


@dataclass
class ShippingInfo:
    """Shipping information for a store."""

    site: str
    shipping_cost: float
    free_over: float

    def calculate_shipping(self, subtotal: float) -> float:
        """Calculate shipping cost for a given subtotal.

        Args:
            subtotal: Order subtotal amount

        Returns:
            Shipping cost (0 if free shipping threshold is met)
        """
        if subtotal >= self.free_over:
            return 0.0
        return self.shipping_cost


@dataclass
class ShippingConfig:
    """Configuration for shipping costs across stores."""

    stores: Dict[str, ShippingInfo]

    @classmethod
    def load_from_file(cls, filepath: str) -> "ShippingConfig":
        """Load shipping configuration from YAML file.

        Args:
            filepath: Path to shipping.yaml file

        Returns:
            ShippingConfig instance

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
            KeyError: If required fields are missing
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        stores = {}
        for entry in data:
            site = entry["site"]
            stores[site] = ShippingInfo(
                site=site,
                shipping_cost=float(entry["shipping"]),
                free_over=float(entry["free-over"]),
            )

        return cls(stores=stores)

    def get_shipping_info(self, site: str, default_shipping: float = 3.99) -> ShippingInfo:
        """Get shipping info for a site, with fallback to default.

        Args:
            site: Site domain
            default_shipping: Default shipping cost if site not found

        Returns:
            ShippingInfo for the site, or default if not found
        """
        if site in self.stores:
            return self.stores[site]

        # Return default shipping info for unknown stores
        return ShippingInfo(
            site=site,
            shipping_cost=default_shipping,
            free_over=NO_FREE_SHIPPING_THRESHOLD,
        )
