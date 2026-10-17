"""The real GDS template: call button -> Conserje number, keypad disabled."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from provisioner.api.schemas import CreatePhoneRequest, UpdatePhoneRequest
from provisioner.generators.gds import GDSGenerator

TEMPLATES = Path(__file__).parent.parent / "templates"

BASE = {
    "mac": "000b82aabbcc",
    "extension": "00001020000",
    "display_name": "Portero Torre GDS",
    "password": "secret",
    "pbx_server": "10.45.40.180",
}


def render(**extra) -> str:
    return GDSGenerator(TEMPLATES).generate_config({**BASE, **extra})


def test_doorbell_number_configures_call_button_and_locks_keypad():
    xml = render(doorbell_number="00000000999")
    assert "<P14827>0</P14827>" in xml          # doorbell mode: call the number
    assert "<P10470>1</P10470>" in xml          # from SIP account 1
    assert "<P10462>00000000999</P10462>" in xml
    assert "<P15421>1</P15421>" in xml          # keypad disabled except the button
    assert "<P15433>1</P15433>" in xml          # no SIP dialing from the keypad


def test_without_doorbell_number_the_button_is_left_alone():
    xml = render(doorbell_number=None)
    for p in ("P14827", "P10462", "P15421", "P15433"):
        assert f"<{p}>" not in xml
    assert "<P404>00001020000</P404>" in xml


@pytest.mark.parametrize("bad", ["999</P10462><P1>x", "12 34", "*99"])
def test_doorbell_number_must_be_digits(bad):
    with pytest.raises(ValidationError):
        UpdatePhoneRequest(doorbell_number=bad)
    with pytest.raises(ValidationError):
        CreatePhoneRequest(**{**BASE, "model": "grandstream_gds3710", "doorbell_number": bad})
