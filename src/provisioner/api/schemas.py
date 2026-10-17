"""Pydantic schemas for API request/response models."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..utils import normalize_mac

# ==================== Phone Schemas ====================


class CreatePhoneRequest(BaseModel):
    """Request schema for creating a phone."""

    mac: str
    model: str
    extension: str
    display_name: str
    password: str
    pbx_server: str | None = None
    pbx_port: int | None = None
    transport: str | None = None
    label: str | None = None
    codecs: list[str] | None = None
    doorbell_number: str | None = None

    @field_validator("mac", mode="before")
    @classmethod
    def normalize_mac_address(cls, v: str) -> str:
        """Normalize MAC address."""
        return normalize_mac(v)

    @field_validator("doorbell_number")
    @classmethod
    def doorbell_number_is_dialable(cls, v: str | None) -> str | None:
        """Digits only: it goes straight into the device config."""
        if v is not None and not v.isdigit():
            raise ValueError("doorbell_number must contain only digits")
        return v


class UpdatePhoneRequest(BaseModel):
    """Request schema for updating a phone."""

    model: str | None = None
    extension: str | None = None
    display_name: str | None = None
    password: str | None = None
    pbx_server: str | None = None
    pbx_port: int | None = None
    transport: str | None = None
    label: str | None = None
    codecs: list[str] | None = None
    doorbell_number: str | None = None

    @field_validator("doorbell_number")
    @classmethod
    def doorbell_number_is_dialable(cls, v: str | None) -> str | None:
        """Digits only: it goes straight into the device config."""
        if v is not None and not v.isdigit():
            raise ValueError("doorbell_number must contain only digits")
        return v


class PhoneResponse(BaseModel):
    """Response schema for a phone."""

    mac: str
    model: str
    extension: str
    display_name: str
    pbx_server: str | None = None
    pbx_port: int | None = None
    transport: str | None = None
    label: str | None = None
    codecs: list[str] | None = None
    doorbell_number: str | None = None
    vendor: str | None = None
    effective_settings: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class PhoneListResponse(BaseModel):
    """Response schema for listing phones."""

    phones: list[PhoneResponse]
    total: int


class PhoneConfigResponse(BaseModel):
    """Response schema for phone config preview."""

    mac: str
    extension: str
    vendor: str
    config: str


# ==================== Phonebook Schemas ====================


class CreatePhonebookEntryRequest(BaseModel):
    """Request schema for creating a phonebook entry."""

    name: str
    number: str


class UpdatePhonebookEntryRequest(BaseModel):
    """Request schema for updating a phonebook entry."""

    name: str | None = None
    number: str | None = None


class PhonebookEntryResponse(BaseModel):
    """Response schema for a phonebook entry."""

    id: int  # Index in the list
    name: str
    number: str

    class Config:
        from_attributes = True


class PhonebookListResponse(BaseModel):
    """Response schema for listing phonebook entries."""

    phonebook_name: str
    entries: list[PhonebookEntryResponse]
    total: int


# ==================== Global Settings Schemas ====================


class GlobalSettingsRequest(BaseModel):
    """Request schema for updating global settings."""

    pbx_server: str
    pbx_port: int = Field(ge=1, le=65535)
    transport: str = Field(pattern="^(UDP|TCP|TLS)$")
    ntp_server: str
    timezone: str
    codecs: list[str]


class GlobalSettingsResponse(BaseModel):
    """Response schema for global settings."""

    pbx_server: str
    pbx_port: int
    transport: str
    ntp_server: str
    timezone: str
    codecs: list[str]

    class Config:
        from_attributes = True


# ==================== System Schemas ====================


class StatsResponse(BaseModel):
    """Response schema for system statistics."""

    phones_configured: int
    phonebook_entries: int
    vendors: list[str]


class ReloadResponse(BaseModel):
    """Response schema for inventory reload."""

    status: str
    phones: int
    phonebook_entries: int


class HealthResponse(BaseModel):
    """Response schema for health check."""

    status: str
    asterisk_enabled: bool = False
    asterisk_connected: bool = False


# ==================== Error Schemas ====================


class ErrorResponse(BaseModel):
    """Response schema for errors."""

    detail: str
