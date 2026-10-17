"""YAML inventory loader for phone definitions and phonebook."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from .utils import normalize_mac


class PhoneEntry(BaseModel):
    """Single phone definition."""

    mac: str
    model: str
    extension: str
    display_name: str
    password: str

    # Optional overrides
    pbx_server: str | None = None
    pbx_port: int | None = None
    transport: str | None = None
    label: str | None = None  # Line label, defaults to display_name
    codecs: list[str] | None = None
    # Door stations: number the call button dials (e.g. the Annuntia Conserje IA)
    doorbell_number: str | None = None

    @field_validator("mac", mode="before")
    @classmethod
    def normalize_mac_address(cls, v: str) -> str:
        """Normalize MAC address on load."""
        return normalize_mac(v)

    @property
    def line_label(self) -> str:
        """Get line label, defaulting to display_name."""
        return self.label or self.display_name


class GlobalSettings(BaseModel):
    """Global settings applied to all phones."""

    pbx_server: str = "pbx.example.com"
    pbx_port: int = 5060
    transport: str = "UDP"
    ntp_server: str = "pool.ntp.org"
    timezone: str = "America/New_York"
    codecs: list[str] = Field(default_factory=lambda: ["PCMU", "PCMA", "G722"])


class PhonebookEntry(BaseModel):
    """Single phonebook entry."""

    name: str
    number: str


class PhonebookGroup(BaseModel):
    """Phonebook group."""

    name: str
    members: list[str] = Field(default_factory=list)


class Inventory(BaseModel):
    """Complete phone inventory."""

    global_settings: GlobalSettings = Field(default_factory=GlobalSettings)
    phones: list[PhoneEntry] = Field(default_factory=list)
    phonebook: list[PhonebookEntry] = Field(default_factory=list)
    phonebook_name: str = "Directory"
    phonebook_groups: list[PhonebookGroup] = Field(default_factory=list)

    # Index for fast MAC lookups
    _mac_index: dict[str, PhoneEntry] = {}

    def model_post_init(self, __context: Any) -> None:
        """Build MAC index after initialization."""
        self._mac_index = {phone.mac: phone for phone in self.phones}

    def get_phone_by_mac(self, mac: str) -> PhoneEntry | None:
        """Look up phone by MAC address."""
        normalized = normalize_mac(mac)
        return self._mac_index.get(normalized)

    def get_effective_settings(self, phone: PhoneEntry) -> dict[str, Any]:
        """Get merged settings for a phone (global + phone-specific)."""
        settings = {
            "pbx_server": phone.pbx_server or self.global_settings.pbx_server,
            "pbx_port": phone.pbx_port or self.global_settings.pbx_port,
            "transport": phone.transport or self.global_settings.transport,
            "ntp_server": self.global_settings.ntp_server,
            "timezone": self.global_settings.timezone,
            "codecs": phone.codecs or self.global_settings.codecs,
            "extension": phone.extension,
            "display_name": phone.display_name,
            "password": phone.password,
            "label": phone.line_label,
            "mac": phone.mac,
            "model": phone.model,
            "doorbell_number": phone.doorbell_number,
        }
        return settings


def load_inventory(inventory_dir: Path | str, secrets_file: Path | str | None = None) -> Inventory:
    """Load inventory from YAML files.

    Args:
        inventory_dir: Directory containing phones.yml and phonebook.yml
        secrets_file: Optional path to secrets.yml for password overrides

    Returns:
        Populated Inventory object
    """
    inventory_dir = Path(inventory_dir)

    # Load phones
    phones_file = inventory_dir / "phones.yml"
    phones_data: dict[str, Any] = {}
    if phones_file.exists():
        with open(phones_file) as f:
            phones_data = yaml.safe_load(f) or {}

    # Load phonebook
    phonebook_file = inventory_dir / "phonebook.yml"
    phonebook_data: dict[str, Any] = {}
    if phonebook_file.exists():
        with open(phonebook_file) as f:
            phonebook_data = yaml.safe_load(f) or {}

    # Load secrets (optional)
    secrets: dict[str, Any] = {}
    if secrets_file:
        secrets_path = Path(secrets_file)
        if secrets_path.exists():
            with open(secrets_path) as f:
                secrets = yaml.safe_load(f) or {}

    # Parse global settings
    global_settings = GlobalSettings(**phones_data.get("global", {}))

    # Parse phones with secret password overrides
    phone_passwords = secrets.get("phone_passwords", {})
    phones: list[PhoneEntry] = []
    for phone_dict in phones_data.get("phones", []):
        ext = phone_dict.get("extension", "")
        # Override password from secrets if available
        if ext in phone_passwords:
            phone_dict["password"] = phone_passwords[ext]
        phones.append(PhoneEntry(**phone_dict))

    # Parse phonebook
    phonebook = [PhonebookEntry(**entry) for entry in phonebook_data.get("phonebook", [])]
    phonebook_name = phonebook_data.get("phonebook_name", "Directory")
    phonebook_groups = [PhonebookGroup(**g) for g in phonebook_data.get("groups", [])]

    return Inventory(
        global_settings=global_settings,
        phones=phones,
        phonebook=phonebook,
        phonebook_name=phonebook_name,
        phonebook_groups=phonebook_groups,
    )


# Global inventory instance
_inventory: Inventory | None = None


def get_inventory() -> Inventory:
    """Get the global inventory instance."""
    global _inventory
    if _inventory is None:
        raise RuntimeError("Inventory not loaded. Call load_inventory() first.")
    return _inventory


def set_inventory(inventory: Inventory) -> None:
    """Set the global inventory instance."""
    global _inventory
    _inventory = inventory
