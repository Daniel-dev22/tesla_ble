"""Tests for Tesla BLE integration.

The Home Assistant stubs live in the root-level :mod:`ha_stubs` module — it has
to be importable *without* loading the ``tesla_ble`` package (which imports
``homeassistant`` at module scope), so it cannot live in this subpackage.
``pytest.ini`` loads it as an early plugin; the call below is a no-op safety net
for direct imports.
"""

from __future__ import annotations

from ha_stubs import install_homeassistant_stubs

install_homeassistant_stubs()
