"""Grandstream phone configuration generator (GXP series)."""

from typing import Any

from .base import BaseGenerator


# Maps codec name → Grandstream P-value codec code
_CODEC_CODE = {
    "PCMU": 0,   # G.711 μ-law
    "PCMA": 8,   # G.711 A-law
    "G722": 9,   # Wideband
    "G729": 18,  # G.729AB
    "G723": 4,   # G.723.1
    "ILBC": 98,  # iLBC
}

# Maps transport name → Grandstream P142 value
_TRANSPORT_CODE = {
    "UDP": 0,
    "TCP": 1,
    "TLS": 2,
}


class GrandstreamGenerator(BaseGenerator):
    """Generator for Grandstream GXP-series phones."""

    VENDOR = "grandstream"
    TEMPLATE_DIR = "grandstream_gxp"
    CONFIG_TEMPLATE = "cfg.xml.j2"
    PHONEBOOK_TEMPLATE = "phonebook.xml.j2"

    @property
    def config_content_type(self) -> str:
        return "application/xml; charset=utf-8"

    def generate_config(self, settings: dict[str, Any]) -> str:
        codec_codes = []
        for name in settings.get("codecs", ["PCMU", "PCMA"]):
            code = _CODEC_CODE.get(name.upper())
            if code is not None:
                codec_codes.append(code)

        transport_code = _TRANSPORT_CODE.get(
            (settings.get("transport") or "UDP").upper(), 0
        )

        return self.render_template(
            self.CONFIG_TEMPLATE,
            codec_codes=codec_codes,
            transport_code=transport_code,
            **settings,
        )

    def generate_phonebook(
        self, entries: list[dict[str, str]], phonebook_name: str = "Directory"
    ) -> str:
        return self.render_template(
            self.PHONEBOOK_TEMPLATE,
            entries=entries,
            phonebook_name=phonebook_name,
        )
