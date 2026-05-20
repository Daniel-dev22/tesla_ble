# Tesla BLE for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/Daniel-dev22/tesla_ble/actions/workflows/validate.yml/badge.svg)](https://github.com/Daniel-dev22/tesla_ble/actions/workflows/validate.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![GitHub release](https://img.shields.io/github/v/release/Daniel-dev22/tesla_ble?include_prereleases)](https://github.com/Daniel-dev22/tesla_ble/releases)

Monitor and control your Tesla **locally over Bluetooth Low Energy (BLE)** from
Home Assistant — no cloud, no Tesla account, no Fleet API, no internet required.

> [!WARNING]
> **Unofficial project.** Not affiliated with, authorized, or endorsed by Tesla,
> Inc. This integration sends real commands to a real vehicle (unlock doors, open
> the frunk/charge port, start climate, control charging). Use it at your own
> risk. "Tesla" and related marks are trademarks of Tesla, Inc.

---

## ⚠️ Safety & liability

**Use this integration entirely at your own risk.** It can physically actuate your
vehicle over Bluetooth. The actions below **physically actuate the car** and can
cause property damage, injury, or leave the vehicle unsecured if triggered at the
wrong moment:

| Physical action | Triggered by |
|---|---|
| Lock / unlock the doors | Lock: *Doors* |
| Unlatch the driver's door | Button: *Unlatch Driver Door* |
| Open the frunk (front trunk) | Cover: *Frunk* · Button: *Open Frunk* |
| Open / close the rear trunk | Cover: *Trunk* |
| Open / vent / close the windows | Cover: *Windows* |
| Open / close the charge port | Cover: *Charge Port* · Button: *Unlock Charge Port* |
| Start / stop charging | Switch: *Charging* |
| Set charge limit (50–100%) | Number: *Charge Limit* |
| Set charging current (1–48 A) | Number: *Charging Amps* |
| Start / stop climate (HVAC) | Switch: *Climate* |
| Toggle defrost | Switch: *Defrost* |
| Toggle steering wheel heater | Switch: *Steering Wheel Heater* |
| Enable / disable Sentry Mode | Switch: *Sentry Mode* |
| Honk the horn | Button: *Honk Horn* |
| Flash the headlights | Button: *Flash Lights* |
| Wake the vehicle | Button: *Wake Vehicle* |
| Enroll a new BLE key (pairing) | Button: *Pair BLE Key* |

Before invoking any control — manually or via an automation — make sure it is safe
to do so. Keep hands, fingers, children, pets, and objects clear of the windows,
frunk, and trunk, and never trigger actions when someone or something could be
harmed, or when doing so would leave the vehicle in an unsafe or insecure state.
Build and test any automations that actuate the car with extreme care.

**No warranty. No liability.** This software is provided "as is", without warranty
of any kind (see [LICENSE](LICENSE), GPLv3 §15–17). The author(s) and contributors
are **not responsible or liable** for any damage, loss, injury, theft, security
exposure, voided warranty, or any other consequence whatsoever arising from the
installation or use of this integration. You alone are responsible for how you use
it and for complying with all applicable laws and Tesla's terms of service.

## Why this integration

- **100% local & cloudless.** All communication is direct BLE to the car. There
  are no calls to Tesla's owner-api or Fleet API, no OAuth, and no account
  credentials. Your pairing keys and session data live only in Home Assistant's
  local storage.
- **★ First-class ESPHome Bluetooth Proxy support.** Built directly on Home
  Assistant's native Bluetooth stack, so any
  [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html)
  that Home Assistant already knows about is used automatically — no extra
  configuration. This lets you reach the car anywhere on your property, not just
  next to the HA host.
  - **Automatic multi-proxy failover & load-balancing.** When several proxies can
    see the vehicle, the integration picks the one with the **strongest signal
    (RSSI)**. If a proxy fails repeatedly, it automatically flips to the next-best
    proxy and puts the failing one on a short cooldown so it doesn't get stuck on
    a flaky or busy node.
  - **Resilient connections** via `bleak-retry-connector` (service caching,
    stale-connection cleanup, sane connect timeouts).
  - 💡 **Tip:** Blanket your property (garage, driveway, street) with multiple
    cheap ESP32 Bluetooth proxies for seamless coverage as the car moves.
- **Smart, adaptive polling.** Polls fast while charging or just-woken, slower
  while parked/asleep — keeping data fresh without keeping the car awake
  unnecessarily.
- **Robust command handling.** Separate prioritized command queues for the
  vehicle's security (VCSEC) and infotainment domains, automatic session
  re-authentication, and wake/sleep + out-of-range detection.

## Requirements

- Home Assistant **2024.1.0** or newer.
- A Tesla vehicle that supports the BLE vehicle-command protocol (Model 3 / Model
  Y; newer Model S / Model X).
- A **connectable** Bluetooth source within range of the vehicle — either a local
  Bluetooth adapter on your HA host, or (recommended) one or more **ESPHome
  Bluetooth Proxies**.
- Your Tesla **key card** (or phone key) to authorize pairing.

Python dependencies (`protobuf`, `cryptography`) are installed automatically by
Home Assistant.

## Installation

### HACS (recommended)

1. In Home Assistant, open **HACS**.
2. Click the **⋮** menu (top-right) → **Custom repositories**.
3. Add the repository URL `https://github.com/Daniel-dev22/tesla_ble` and select
   category **Integration**.
4. Search for **Tesla BLE**, open it, and click **Download**.
5. **Restart Home Assistant.**

### Manual

1. Download the latest [release](https://github.com/Daniel-dev22/tesla_ble/releases).
2. Copy all files into `config/custom_components/tesla_ble/`.
3. **Restart Home Assistant.**

## Setup & pairing

### How pairing works

Pairing enrolls Home Assistant as a **BLE key** on your vehicle — the same
mechanism Tesla uses for phone keys and key fobs:

1. Home Assistant generates a cryptographic **key pair** locally. The **private
   key never leaves** Home Assistant's local storage; only the **public key** is
   enrolled on the car.
2. Over BLE, the integration asks the vehicle to add that public key to its
   **whitelist** (the vehicle's VCSEC security domain).
3. You **physically authorize** the new key by tapping an existing key card on the
   center-console reader — proving you have access to the car. This is why pairing
   must be done **in person**; it cannot be done remotely.
4. From then on, Home Assistant **signs every command** with its private key and
   the vehicle trusts it. No Tesla account, cloud, or internet is involved.

### Before you start

- Be **inside / next to the vehicle** with an existing authorized key (key card or
  phone key).
- The vehicle must be **awake** and **within Bluetooth range** of a connectable
  adapter or ESPHome proxy.

### Steps

1. **Settings → Devices & Services → Add Integration → Tesla BLE.**
2. Enter your vehicle's **17-character VIN** (and an optional device name). The
   integration locates the car by the BLE name it advertises, which is derived
   from the VIN — so the VIN must be exact.
3. If more than one adapter/proxy sees the car, pick the device to pair through.
4. When prompted, **inside the car**:
   - Put the vehicle in **Park**.
   - On the touchscreen: **Controls → Locks → Add Key**.
   - Select **"Key Fob"** when prompted.
   - **Tap your key card** on the center-console card reader to authorize the new
     key.
5. Home Assistant confirms enrollment, then lets you set your **polling**
   preferences. Done.

### After pairing

Keys and session data are stored only in Home Assistant's local storage, and
sessions re-establish automatically (including after a restart). If you ever need
to pair again — for example after removing the key on the car — use the **Pair BLE
Key** button on the device.

### If pairing fails

The flow reports the specific reason so you can fix it and retry:

- **Valet Mode** is enabled — disable it and retry.
- The key is **already on the whitelist** — remove it on the car first, or use a
  different key.
- The key has **no permission** to be added — use an authorized key.
- The request was **denied or cancelled** on the touchscreen — accept it on the
  car and retry.
- The **card tap timed out** — tap your key card promptly when the car prompts.
- **Cannot connect / no devices found** — confirm the car is awake and within
  range of a *connectable* Bluetooth source.

## Supported entities

The integration exposes **~40+ entities** across the platforms below. There is no
Home Assistant `climate` entity — climate is exposed as discrete switches, binary
sensors, and temperature sensors (rows marked *climate*).

### Sensors

| Entity | Description |
|---|---|
| Charge Level | Battery state of charge (%) |
| Charge Limit | Configured charge limit (%) |
| Range | Estimated remaining range |
| Charging State | Disconnected / Stopped / Charging / Complete |
| Charge Current | Actual charging current (A) |
| Charge Voltage | Charging voltage (V) |
| Charge Power | Charging power (kW) |
| Charge Energy Added | Energy added this charge session (kWh) |
| Charge Miles Added | Range added this charge session |
| Minutes to Limit | Estimated minutes until the charge limit is reached |
| Requested Charge Current | Charge current requested by the vehicle (A) |
| Interior Temperature | Cabin temperature *(climate)* |
| Exterior Temperature | Outside temperature *(climate)* |
| Odometer | Total distance traveled |
| Vehicle Power | Instantaneous vehicle power |
| Shift State | P / R / N / D |
| GPS Timestamp | Time of the last GPS fix |
| Defrost Mode | Current defrost mode *(climate)* |
| Sentry Mode State | Current Sentry Mode state |
| Tire Pressure — Front Left / Front Right / Rear Left / Rear Right | Per-wheel tire pressure |
| Tire Pressure — Recommended Front / Recommended Rear | Recommended tire pressures |
| BLE Signal | RSSI of the connected Bluetooth proxy / adapter |

### Binary sensors

| Entity | Description |
|---|---|
| Asleep | Whether the vehicle is asleep |
| User Present | Whether a user / driver is present |
| Doors Locked | Door lock state |
| Charge Port Open | Charge port door open |
| Driver Front / Driver Rear / Passenger Front / Passenger Rear Door Open | Per-door open state |
| Climate On | Whether climate is running *(climate)* |
| Defrost | Whether defrost is active *(climate)* |
| Frunk Open | Front trunk open |
| Trunk Open | Rear trunk open |
| Windows Open | Any window open |
| Sentry Mode | Sentry Mode active |
| Preconditioning | Battery / cabin preconditioning active *(climate)* |
| Steering Wheel Heater | Steering wheel heater on *(climate)* |

### Switches

| Entity | Description |
|---|---|
| Charging | Start / stop charging |
| Climate | Turn climate (HVAC) on / off *(climate)* |
| Defrost | Toggle defrost *(climate)* |
| Steering Wheel Heater | Toggle steering wheel heater *(climate)* |
| Sentry Mode | Enable / disable Sentry Mode |

### Buttons

| Entity | Description |
|---|---|
| Pair BLE Key | Start BLE key pairing with the vehicle |
| Honk Horn | Honk the horn |
| Flash Lights | Flash the headlights |
| Wake Vehicle | Wake the vehicle from sleep |
| Open Frunk | Open the front trunk |
| Unlock Charge Port | Unlock / open the charge port |
| Unlatch Driver Door | Unlatch the driver's door |

### Lock

| Entity | Description |
|---|---|
| Doors | Lock / unlock the doors |

### Covers

| Entity | Description |
|---|---|
| Frunk | Open the front trunk (open only) |
| Trunk | Open / close the rear trunk |
| Charge Port | Open / close the charge port |
| Windows | Vent / close the windows |

### Numbers

| Entity | Range | Description |
|---|---|---|
| Charge Limit | 50–100% | Set the charge limit |
| Charging Amps | 1–48 A | Set the charging current |

## Configuration (polling)

All cadences are configurable during setup and later via the integration's
**Configure** option. Defaults mirror the ESPHome Tesla BLE component:

| Setting | Default | Description |
|---|---|---|
| Update Interval | `10 s` | VCSEC keepalive poll cadence |
| Fast Poll Duration After Wake | `300 s` | How long to poll quickly after the car wakes |
| Awake Poll Period | `60 s` | Data poll cadence while awake |
| Asleep Poll Period | `60 s` | Data poll cadence while asleep |
| Charging Poll Period | `10 s` | Fast data poll cadence while charging |
| Offline Grace Period | `300 s` | Delay before marking the device unavailable |
| Fast Poll When Unlocked | `0` | Poll quickly while the car is unlocked (`0`/`1`) |
| Wake Vehicle On Startup | `0` | Wake the car when HA starts (`0`/`1`) |

## Troubleshooting

- **"No Tesla BLE devices found nearby."** The car must be awake and within range
  of a **connectable** Bluetooth source. Passive-only scanners won't work — use a
  local adapter or an ESPHome proxy configured for active connections.
- **Pairing tap timed out.** Re-run pairing and tap your key card on the
  center-console reader promptly when the car prompts you.
- **Flaky connections in a large property.** Add more ESPHome Bluetooth proxies;
  the integration will automatically use whichever proxy has the best signal and
  fail over between them.

## Credits

- Protobuf definitions are generated from Tesla's open-source
  [`vehicle-command`](https://github.com/teslamotors/vehicle-command) repository
  (Apache License 2.0). See [`proto/README.md`](proto/README.md) for regeneration
  details.
- Architectural reference: the ESPHome
  [Tesla BLE](https://github.com/yoziru/esphome-tesla-ble) component.

## License

Licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE).
