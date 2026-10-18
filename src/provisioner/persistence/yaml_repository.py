"""YAML repository for persistent storage of phones, phonebook, and settings."""

import logging
from pathlib import Path
from typing import Any

import yaml

from ..exceptions import (
    DuplicateExtensionError,
    DuplicateMACError,
    PersistenceError,
    PhonebookEntryNotFoundError,
    PhoneNotFoundError,
)
from ..inventory import (
    GlobalSettings,
    Inventory,
    PhonebookEntry,
    PhoneEntry,
    load_inventory,
    set_inventory,
)
from ..utils import normalize_mac
from .backup import BackupManager

logger = logging.getLogger("provisioner.persistence")


class YAMLRepository:
    """Handles atomic YAML read/write operations with backup."""

    def __init__(self, inventory_dir: Path | str, secrets_file: Path | str | None = None):
        """Initialize YAML repository.

        Args:
            inventory_dir: Directory containing phones.yml and phonebook.yml
            secrets_file: Optional path to secrets.yml for password overrides
        """
        self.inventory_dir = Path(inventory_dir)
        self.secrets_file = Path(secrets_file) if secrets_file else None
        self.phones_file = self.inventory_dir / "phones.yml"
        self.phonebook_file = self.inventory_dir / "phonebook.yml"

        # Setup backup manager
        backup_dir = self.inventory_dir / ".backups"
        self.backup_manager = BackupManager(backup_dir, max_backups=10)

        # Ensure inventory directory exists
        self.inventory_dir.mkdir(parents=True, exist_ok=True)

    # ==================== Phone Operations ====================

    def add_phone(self, phone: PhoneEntry) -> None:
        """Add a phone to phones.yml and secrets.yml.

        Args:
            phone: Phone entry to add

        Raises:
            DuplicateMACError: If phone with this MAC already exists
            DuplicateExtensionError: If extension is already in use
            PersistenceError: If YAML write fails
        """
        # Load current inventory to check for duplicates
        inventory = load_inventory(self.inventory_dir, self.secrets_file)

        # Check for duplicate MAC
        if inventory.get_phone_by_mac(phone.mac):
            raise DuplicateMACError(f"Phone with MAC {phone.mac} already exists")

        # Check for duplicate extension
        if not self._is_extension_available(inventory, phone.extension):
            raise DuplicateExtensionError(f"Extension {phone.extension} is already in use")

        # Load current YAML data
        phones_data = self._load_yaml(self.phones_file)

        # Add phone to phones list
        phone_dict = {
            "mac": phone.mac,
            "model": phone.model,
            "extension": phone.extension,
            "display_name": phone.display_name,
            "password": phone.password,  # This will be moved to secrets if secrets_file exists
        }

        # Add optional fields if present
        if phone.pbx_server:
            phone_dict["pbx_server"] = phone.pbx_server
        if phone.pbx_port:
            phone_dict["pbx_port"] = phone.pbx_port
        if phone.transport:
            phone_dict["transport"] = phone.transport
        if phone.label:
            phone_dict["label"] = phone.label
        if phone.codecs:
            phone_dict["codecs"] = phone.codecs
        if phone.doorbell_number:
            phone_dict["doorbell_number"] = phone.doorbell_number

        phones_data.setdefault("phones", []).append(phone_dict)

        # Write phones.yml
        self._atomic_write_yaml(self.phones_file, phones_data)

        # Update secrets.yml if it exists
        if self.secrets_file and self.secrets_file.exists():
            self._update_secret_password(phone.extension, phone.password)
            # Remove password from phones.yml
            phone_dict.pop("password", None)
            self._atomic_write_yaml(self.phones_file, phones_data)

        # Reload inventory singleton
        self._reload_inventory()

        logger.info(f"Added phone {phone.mac} (extension {phone.extension})")

    def update_phone(self, mac: str, updates: dict[str, Any]) -> None:
        """Update a phone in phones.yml.

        Args:
            mac: MAC address of phone to update (will be normalized)
            updates: Dictionary of fields to update

        Raises:
            PhoneNotFoundError: If phone not found
            DuplicateExtensionError: If changing to an in-use extension
            PersistenceError: If YAML write fails
        """
        normalized_mac = normalize_mac(mac)

        # Load current data
        phones_data = self._load_yaml(self.phones_file)
        phones_list = phones_data.get("phones", [])

        # Find phone to update
        phone_index = None
        for i, phone_dict in enumerate(phones_list):
            if normalize_mac(phone_dict["mac"]) == normalized_mac:
                phone_index = i
                break

        if phone_index is None:
            raise PhoneNotFoundError(f"Phone {normalized_mac} not found")

        current_phone = phones_list[phone_index]
        old_extension = current_phone.get("extension")

        # Check if extension is changing and if it's available
        if "extension" in updates and updates["extension"] != current_phone["extension"]:
            inventory = load_inventory(self.inventory_dir, self.secrets_file)
            if not self._is_extension_available(
                inventory, updates["extension"], exclude_mac=normalized_mac
            ):
                raise DuplicateExtensionError(f"Extension {updates['extension']} is already in use")

        # Update phone fields
        for key, value in updates.items():
            if key == "password":
                # Handle password separately - store in secrets if secrets file exists
                if self.secrets_file and self.secrets_file.exists():
                    # If extension is changing, update with new extension, otherwise use current
                    ext_for_password = updates.get("extension", old_extension)
                    self._update_secret_password(ext_for_password, value)
                    # Don't add password to phones.yml
                    continue
                else:
                    # No secrets file, store password in phones.yml
                    current_phone[key] = value
            else:
                current_phone[key] = value

        # Write updated data
        self._atomic_write_yaml(self.phones_file, phones_data)

        # If extension changed and secrets file exists, move password to new extension
        if "extension" in updates and old_extension != updates["extension"] and self.secrets_file:
            secrets_data = self._load_yaml(self.secrets_file)
            phone_passwords = secrets_data.get("phone_passwords", {})
            if old_extension in phone_passwords and "password" not in updates:
                # Move existing password to new extension
                phone_passwords[updates["extension"]] = phone_passwords[old_extension]
                del phone_passwords[old_extension]
                self._atomic_write_yaml(self.secrets_file, secrets_data)

        # Reload inventory
        self._reload_inventory()

        logger.info(f"Updated phone {normalized_mac}")

    def delete_phone(self, mac: str) -> None:
        """Remove a phone from phones.yml and secrets.yml.

        Args:
            mac: MAC address of phone to delete

        Raises:
            PhoneNotFoundError: If phone not found
            PersistenceError: If YAML write fails
        """
        normalized_mac = normalize_mac(mac)

        # Load current data
        phones_data = self._load_yaml(self.phones_file)
        phones_list = phones_data.get("phones", [])

        # Find and remove phone
        phone_index = None
        phone_extension = None
        for i, phone_dict in enumerate(phones_list):
            if normalize_mac(phone_dict["mac"]) == normalized_mac:
                phone_index = i
                phone_extension = phone_dict.get("extension")
                break

        if phone_index is None:
            raise PhoneNotFoundError(f"Phone {normalized_mac} not found")

        # Remove phone from list
        phones_list.pop(phone_index)

        # Write updated data
        self._atomic_write_yaml(self.phones_file, phones_data)

        # Remove password from secrets if it exists
        if phone_extension and self.secrets_file:
            self._remove_secret_password(phone_extension)

        # Reload inventory
        self._reload_inventory()

        logger.info(f"Deleted phone {normalized_mac} (extension {phone_extension})")

    # ==================== Global Settings Operations ====================

    def update_global_settings(self, settings: GlobalSettings) -> None:
        """Update global settings in phones.yml.

        Args:
            settings: New global settings

        Raises:
            PersistenceError: If YAML write fails
        """
        phones_data = self._load_yaml(self.phones_file)

        # Update global section
        phones_data["global"] = {
            "pbx_server": settings.pbx_server,
            "pbx_port": settings.pbx_port,
            "transport": settings.transport,
            "ntp_server": settings.ntp_server,
            "timezone": settings.timezone,
            "codecs": settings.codecs,
        }

        # Write updated data
        self._atomic_write_yaml(self.phones_file, phones_data)

        # Reload inventory
        self._reload_inventory()

        logger.info("Updated global settings")

    # ==================== Phonebook Operations ====================

    def add_phonebook_entry(self, entry: PhonebookEntry) -> None:
        """Add entry to phonebook.yml.

        Args:
            entry: Phonebook entry to add

        Raises:
            PersistenceError: If YAML write fails
        """
        phonebook_data = self._load_yaml(self.phonebook_file)

        entry_dict = {
            "name": entry.name,
            "number": entry.number,
        }

        phonebook_data.setdefault("phonebook", []).append(entry_dict)

        self._atomic_write_yaml(self.phonebook_file, phonebook_data)
        self._reload_inventory()

        logger.info(f"Added phonebook entry: {entry.name}")

    def update_phonebook_entry(self, index: int, entry: PhonebookEntry) -> None:
        """Update entry in phonebook.yml.

        Args:
            index: Index of entry to update (0-based)
            entry: Updated phonebook entry

        Raises:
            PhonebookEntryNotFoundError: If index out of range
            PersistenceError: If YAML write fails
        """
        phonebook_data = self._load_yaml(self.phonebook_file)
        phonebook_list = phonebook_data.get("phonebook", [])

        if index < 0 or index >= len(phonebook_list):
            raise PhonebookEntryNotFoundError(f"Phonebook entry index {index} not found")

        phonebook_list[index] = {
            "name": entry.name,
            "number": entry.number,
        }

        self._atomic_write_yaml(self.phonebook_file, phonebook_data)
        self._reload_inventory()

        logger.info(f"Updated phonebook entry {index}: {entry.name}")

    def delete_phonebook_entry(self, index: int) -> None:
        """Remove entry from phonebook.yml.

        Args:
            index: Index of entry to delete (0-based)

        Raises:
            PhonebookEntryNotFoundError: If index out of range
            PersistenceError: If YAML write fails
        """
        phonebook_data = self._load_yaml(self.phonebook_file)
        phonebook_list = phonebook_data.get("phonebook", [])

        if index < 0 or index >= len(phonebook_list):
            raise PhonebookEntryNotFoundError(f"Phonebook entry index {index} not found")

        removed_entry = phonebook_list.pop(index)

        self._atomic_write_yaml(self.phonebook_file, phonebook_data)
        self._reload_inventory()

        logger.info(f"Deleted phonebook entry {index}: {removed_entry.get('name')}")

    # ==================== Helper Methods ====================

    def _is_extension_available(
        self, inventory: Inventory, extension: str, exclude_mac: str | None = None
    ) -> bool:
        """Check if an extension is available.

        Args:
            inventory: Current inventory
            extension: Extension to check
            exclude_mac: MAC address to exclude from check (for updates)

        Returns:
            True if extension is available, False otherwise
        """
        for phone in inventory.phones:
            if phone.extension == extension:
                if exclude_mac and phone.mac == normalize_mac(exclude_mac):
                    continue
                return False
        return True

    def _load_yaml(self, file_path: Path) -> dict[str, Any]:
        """Load YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed YAML data

        Raises:
            PersistenceError: If file read fails
        """
        try:
            if not file_path.exists():
                return {}

            with open(file_path) as f:
                data = yaml.safe_load(f)
                return data or {}
        except Exception as e:
            raise PersistenceError(f"Failed to load {file_path}: {e}")

    def _atomic_write_yaml(self, file_path: Path, data: dict[str, Any]) -> None:
        """Write YAML atomically: backup → write temp → validate → rename.

        Args:
            file_path: Path to YAML file
            data: Data to write

        Raises:
            PersistenceError: If write fails
        """
        temp_path = file_path.with_suffix(".tmp")
        backup_path = None

        try:
            # 1. Create backup if file exists
            if file_path.exists():
                backup_path = self.backup_manager.create_backup(file_path)

            # 2. Write to temporary file
            with open(temp_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

            # 3. Validate YAML can be parsed
            with open(temp_path) as f:
                yaml.safe_load(f)

            # 4. Atomic rename
            temp_path.replace(file_path)

            logger.debug(f"Successfully wrote {file_path}")

        except Exception as e:
            # Rollback from backup on failure
            if backup_path and backup_path.exists() and file_path.exists():
                self.backup_manager.restore_backup(backup_path, file_path)
                logger.warning(f"Rolled back {file_path} from backup after error")

            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()

            raise PersistenceError(f"Failed to write {file_path}: {e}")

    def _update_secret_password(self, extension: str, password: str) -> None:
        """Update password in secrets.yml.

        Args:
            extension: Extension number
            password: Password to set
        """
        if not self.secrets_file:
            return

        secrets_data = self._load_yaml(self.secrets_file)
        secrets_data.setdefault("phone_passwords", {})[extension] = password
        self._atomic_write_yaml(self.secrets_file, secrets_data)

    def _remove_secret_password(self, extension: str) -> None:
        """Remove password from secrets.yml.

        Args:
            extension: Extension number
        """
        if not self.secrets_file or not self.secrets_file.exists():
            return

        secrets_data = self._load_yaml(self.secrets_file)
        phone_passwords = secrets_data.get("phone_passwords", {})

        if extension in phone_passwords:
            del phone_passwords[extension]
            self._atomic_write_yaml(self.secrets_file, secrets_data)

    def _reload_inventory(self) -> None:
        """Reload inventory singleton from disk."""
        inventory = load_inventory(self.inventory_dir, self.secrets_file)
        set_inventory(inventory)
        logger.debug("Reloaded inventory from disk")
