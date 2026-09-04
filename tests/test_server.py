"""Tests for the FastAPI server."""

import tempfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient


# We need to set up the environment before importing the server
@pytest.fixture
def test_environment():
    """Create a temporary environment with config and inventory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create config
        config = {
            "server": {"host": "0.0.0.0", "port": 8080, "log_level": "WARNING", "json_logs": False},
            "paths": {
                "inventory_dir": "inventory",
                "templates_dir": "templates",
                "secrets_file": "inventory/secrets.yml",
            },
            "pbx": {"server": "test-pbx.local", "port": 5060},
            "vendor_oui": {
                "yealink": ["001565"],
                "fanvil": ["0C383E"],
            },
        }

        with open(tmpdir / "config.yml", "w") as f:
            yaml.dump(config, f)

        # Create inventory directory
        inv_dir = tmpdir / "inventory"
        inv_dir.mkdir()

        phones = {
            "global": {"pbx_server": "test-pbx.local", "pbx_port": 5060},
            "phones": [
                {
                    "mac": "00:15:65:AA:BB:CC",
                    "model": "yealink_t23g",
                    "extension": "101",
                    "display_name": "Test Yealink",
                    "password": "yealinkpass",
                },
                {
                    "mac": "0C:38:3E:11:22:33",
                    "model": "fanvil_v64",
                    "extension": "102",
                    "display_name": "Test Fanvil",
                    "password": "fanvilpass",
                },
                {
                    "mac": "00:0B:82:AA:BB:CC",
                    "model": "grandstream_gds3710",
                    "extension": "0010010000",
                    "display_name": "Test GDS3710",
                    "password": "gdspass",
                },
            ],
        }

        with open(inv_dir / "phones.yml", "w") as f:
            yaml.dump(phones, f)

        phonebook = {
            "phonebook_name": "Test Directory",
            "phonebook": [
                {"name": "Test Yealink", "number": "101"},
                {"name": "Test Fanvil", "number": "102"},
            ],
        }

        with open(inv_dir / "phonebook.yml", "w") as f:
            yaml.dump(phonebook, f)

        # Create templates directory
        tpl_dir = tmpdir / "templates"
        tpl_dir.mkdir()

        # Yealink templates
        yealink_dir = tpl_dir / "yealink_t23g"
        yealink_dir.mkdir()

        with open(yealink_dir / "mac.cfg.j2", "w") as f:
            f.write("""#!version:1.0.0.1
account.1.enable = 1
account.1.user_name = {{ extension }}
account.1.password = {{ password }}
account.1.sip_server.1.address = {{ pbx_server }}
""")

        with open(yealink_dir / "phonebook.xml.j2", "w") as f:
            f.write("""<?xml version="1.0"?>
<YealinkIPPhoneDirectory>
{% for entry in entries %}
<DirectoryEntry><n>{{ entry.name }}</n><Telephone>{{ entry.number }}</Telephone></DirectoryEntry>
{% endfor %}
</YealinkIPPhoneDirectory>
""")

        # Fanvil templates
        fanvil_dir = tpl_dir / "fanvil_v64"
        fanvil_dir.mkdir()

        with open(fanvil_dir / "mac.cfg.j2", "w") as f:
            f.write("""<< VOIP CONFIG FILE >>Version:2.0001
SIP1 Enable = 1
SIP1 User ID = {{ extension }}
SIP1 Authenticate Password = {{ password }}
SIP1 Server Address = {{ pbx_server }}
""")

        with open(fanvil_dir / "phonebook.xml.j2", "w") as f:
            f.write("""<?xml version="1.0"?>
<FanvilIPPhoneDirectory>
{% for entry in entries %}
<DirectoryEntry><n>{{ entry.name }}</n><Telephone>{{ entry.number }}</Telephone></DirectoryEntry>
{% endfor %}
</FanvilIPPhoneDirectory>
""")

        # Grandstream GDS templates
        gds_dir = tpl_dir / "grandstream_gds"
        gds_dir.mkdir()

        with open(gds_dir / "cfg.xml.j2", "w") as f:
            f.write("""<?xml version="1.0" encoding="UTF-8" ?>
<gs_provision version="1">
  <config version="1">
    <P402>{{ pbx_server }}</P402>
    <P404>{{ extension }}</P404>
    <P406>{{ password }}</P406>
    <P407>{{ display_name }}</P407>
  </config>
</gs_provision>
""")

        yield tmpdir


@pytest.fixture
def client(test_environment, monkeypatch):
    """Create test client with configured environment."""
    import os

    # Change to test directory so config.yml is found
    original_cwd = os.getcwd()
    os.chdir(test_environment)

    # Import after changing directory
    from provisioner.server import app

    with TestClient(app) as client:
        yield client

    os.chdir(original_cwd)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestStatsEndpoint:
    """Tests for /stats endpoint."""

    def test_stats(self, client):
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["phones_configured"] == 3
        assert data["phonebook_entries"] == 2


class TestAutoProvision:
    """Tests for auto-detect provisioning."""

    def test_provision_yealink_auto(self, client):
        response = client.get("/001565aabbcc.cfg")
        assert response.status_code == 200
        assert "account.1.user_name = 101" in response.text

    def test_provision_fanvil_auto(self, client):
        response = client.get("/0c383e112233.cfg")
        assert response.status_code == 200
        assert "SIP1 User ID = 102" in response.text

    def test_provision_not_found(self, client):
        response = client.get("/aabbccddeeff.cfg")
        assert response.status_code == 404


class TestVendorSpecificProvision:
    """Tests for vendor-specific endpoints."""

    def test_yealink_endpoint(self, client):
        response = client.get("/yealink/001565aabbcc.cfg")
        assert response.status_code == 200
        assert "#!version:1.0.0.1" in response.text

    def test_fanvil_endpoint(self, client):
        response = client.get("/fanvil/0c383e112233.cfg")
        assert response.status_code == 200
        assert "<< VOIP CONFIG FILE >>" in response.text


class TestGDSProvision:
    """Tests for the GDS37xx door-panel provisioning endpoint."""

    def test_gds_endpoint(self, client):
        response = client.get("/grandstream_gds/000b82aabbcc.xml")
        assert response.status_code == 200
        assert "<P404>0010010000</P404>" in response.text
        assert "<P406>gdspass</P406>" in response.text

    def test_gds_auto_detect_by_model(self, client):
        """provision_auto (/{mac}.cfg) looks up vendor via _detect() and
        serves whatever generator matches — it has no special-case that
        excludes Grandstream despite its docstring's "redirects GS to XML"
        phrasing (that describes operational intent, not existing code).
        Once _detect() routes grandstream_gds3710 to "grandstream_gds" (a
        real key in `generators`), this endpoint serves it like any other
        vendor."""
        response = client.get("/000b82aabbcc.cfg")
        assert response.status_code == 200
        assert "<P404>0010010000</P404>" in response.text


class TestPhonebook:
    """Tests for phonebook endpoints."""

    def test_yealink_phonebook(self, client):
        response = client.get("/phonebook.xml")
        assert response.status_code == 200
        assert "YealinkIPPhoneDirectory" in response.text
        assert "Test Yealink" in response.text

    def test_fanvil_phonebook(self, client):
        response = client.get("/fanvil/phonebook.xml")
        assert response.status_code == 200
        assert "FanvilIPPhoneDirectory" in response.text


class TestReload:
    """Tests for inventory reload."""

    def test_reload(self, client):
        response = client.get("/reload")
        assert response.status_code == 200
        assert response.json()["status"] == "reloaded"
