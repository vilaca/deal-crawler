"""YAML data loader for product URLs."""

import sys
from typing import Dict, List

import yaml


def load_products(yaml_file: str) -> Dict[str, List[str]]:
    """Load products and URLs from YAML file."""
    try:
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

            if data is None:
                print(f"Error: '{yaml_file}' is empty", file=sys.stderr)
                return {}

            if not isinstance(data, dict):
                print(
                    f"Error: '{yaml_file}' must contain a dictionary " f"at the root level",
                    file=sys.stderr,
                )
                return {}

            # Validate structure: dict of product names to list of URLs
            for product_name, urls in data.items():
                if not isinstance(urls, list):
                    print(
                        f"Warning: Product '{product_name}' does not have " f"a list of URLs, skipping",
                        file=sys.stderr,
                    )
                    data[product_name] = []
                elif not all(isinstance(url, str) for url in urls):
                    print(
                        f"Warning: Product '{product_name}' contains " f"non-string URLs",
                        file=sys.stderr,
                    )

            return data

    except FileNotFoundError:
        print(f"Error: File '{yaml_file}' not found", file=sys.stderr)
        print(f"Please create '{yaml_file}' with your product URLs", file=sys.stderr)
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Unexpected error loading '{yaml_file}': {e}", file=sys.stderr)
        return {}
