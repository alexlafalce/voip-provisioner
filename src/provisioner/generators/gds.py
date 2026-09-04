"""Grandstream GDS37xx door system configuration generator.

Distinct P-value namespace from GXP-series phones (generators/grandstream.py) —
verified against the official BroadSoft/Grandstream GDS37xx reference
configuration. Do not merge with GrandstreamGenerator or reuse its P-values.
"""

from typing import Any

from .base import BaseGenerator


class GDSGenerator(BaseGenerator):
    """Generator for Grandstream GDS37xx door systems (GDS3705/GDS3710)."""

    VENDOR = "grandstream_gds"
    TEMPLATE_DIR = "grandstream_gds"
    CONFIG_TEMPLATE = "cfg.xml.j2"
    PHONEBOOK_TEMPLATE = None  # door panels don't have a phonebook in this integration

    @property
    def config_content_type(self) -> str:
        return "application/xml; charset=utf-8"

    def generate_config(self, settings: dict[str, Any]) -> str:
        return self.render_template(self.CONFIG_TEMPLATE, **settings)

    def generate_phonebook(
        self, entries: list[dict[str, str]], phonebook_name: str = "Directory"
    ) -> str:
        raise NotImplementedError("GDS37xx door panels don't support a phonebook in this integration")
