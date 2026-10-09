# Active Thermo-IoT harvester PCB candidate A0 (LTC3108GN16)

## Important status

This folder contains **native KiCad schematic/net-assigned PCB for an LTC3108 active power breakout**, not a finalized complete industrial IoT device. The PCB has placed parts, assigned nets, and **two explicitly routed charge-pump connections** (C1.2→U1.13, C2.2→U1.14); the remainder is still UNROUTED. It has NOT passed a real KiCad ERC/DRC, mechanical clearance checks, assembly inspection, or hot/cold-start testing. **Do NOT send to PCB fabrication as is.**

The design uses the **LTC3108EGN** 16-pin SSOP package and an **external transformer** for ease of bench swapping. Pin numbering matches the manufacturer GN16 top-view drawing (Rev D). Manufacturer typical application: https://www.analog.com/media/en/technical-documentation/data-sheets/3108fc.pdf.

## Architecture and rationale

J1 TEG source -> C5 reservoir + primary of external 1:100 transformer (J2 primary TEG_P to SW). Secondary ground/Sec_HI -> C1 1nF and C2 330pF -> LTC3108's C1/C2 charge pump. VS1=VAUX and VS2=GND selects **3.3V** VOUT. C3 1uF VAUX, C4 2.2uF VLDO. J3 exposes VOUT with C6 470uF. J4 exposes 5V VSTORE for an external 0.1F / 6.3V energy reservoir (C7 DNP). J5 exposes PGD for a **high-impedance** diagnostic probe. VOUT2_EN tied to GND, VOUT2 unused.

**Critical:** J2 four-pin 2.54mm transformer breakout does not correspond to the transformer manufacturer's surface-mount pad numbering. Confirm coil polarity/pinout and orientation on the real LPR6235 before assembly; no transformer is soldered on this PCB.

| IC pin | Function | Circuit net |
|---|---|---|
| 1, 8, 9, 16 | GND | GND |
| 2 | VAUX | VAUX |
| 3 | VSTORE | VSTORE |
| 4 | VOUT | VOUT |
| 5 | VOUT2 | NC_VOUT2 / unconnected |
| 6 | VLDO | VLDO |
| 7 | PGD | PGD |
| 10 | VS2 | GND |
| 11 | VS1 | VAUX |
| 12 | VOUT2_EN | GND |
| 13 | C1 | PMIC_C1 |
| 14 | C2 | PMIC_C2 |
| 15 | SW | SW |

## Stop/go constraints

* **Minimum 20mV** LTC3108 startup is datasheet input voltage under a 1:100 transformer, NOT a claim about any particular TEG, output current, zero gradient or autonomous 87mA radio peaks.
* LTC3108 VOUT current limit from datasheet ~2.8–7.5 mA (typ ~4.5mA), far below potential LoRa high-power pulses; **supply RF from measured reservoir energy**, and implement supervised power gating, hold-up / ESR tests, and output supply-current limits.
* VSTORE operates at about 5 V, **not acceptable as direct STM32WLE supply**. Connect MCU only to verified VOUT 3.3 V rail (and review startup/sag).
* The selected capacitor footprints / dimensions are *placeholders*, not approved mechanical data. Choose actual vendor MPNs, tolerances, lead pitch, ESR and leakage, and recalculate hold-up before routing.
* Avoid connecting J1 to live district heating conductors, mains, or unqualified hot surfaces. All measurements must be done on a controlled isolated low-voltage thermal rig.

## Required remaining manufacturing gates

1. Exact BOM manufacturers, cap lead pitch, Coilcraft winding pin mapping, safe VS1 selection and TEG voltage/current envelope verified.
2. KiCad opens schematic and PCB and reports **zero blocking ERC/DRC**, zero unconnected nets after a proper manual route, correct pad/net parity, mask clearance and track capacity.
3. Independent review of thermal, electrical and RF wiring and source mechanical drawings.
4. Gerber + Excellon drill exports and independent preview; then limited prototype fabrication with current-limited bench bring-up.
5. Cold-start, brownout, leakage, ESR and peak TX/RX validation. No claims of measured performance until archived data exists.

## Footprint source library

The local `ThermoActive.pretty/` directory and `fp-lib-table` resolve the custom SMD/TH footprints used in the schematic. They are **engineering placeholders**, not manufacturer-validated land patterns. In particular, `RadialCap` stands for an unselected 2.54mm-pitch THT cap and can be dangerous if a larger diameter, different polarity, clearance or thermal derating is required. The SSOP16 land-pattern is provisional and must be compared with Analog Devices GN16 recommended solder pattern before release.

## Routing progress — 9 Oct 2026 (A0 candidate; NOT FOR FAB)

The **manufacturer-reference** capacitor-to-LTC3108 nets `PMIC_C1` and `PMIC_C2` have now been laid on F.Cu at 0.20 mm nominal width. The real KiCad 10.0.6 DRC diagnostics [37960523837](https://github.com/mojealterego/FENG-LABORATORY/actions/runs/37960523837) report **28 unconnected pads remaining**, down from 30, and **13 existing footprint-library mismatch warnings**. There were no new inter-track violations reported for the two routed nets. These are preliminary reference-board traces, **not an undisclosed novel circuit**. Transformer pin order, capacitor land-patterns, ESR, clearance, and all other wiring remain HOLD; the board shall not be manufactured or attached to live heating infrastructure without independent electrical/DFM validation.

`hardware/cad_gate.py` interprets KiCad textual DRC to machine-readable `HOLD` / `ENGINEERING_REVIEW_REQUIRED`. Even a hypothetical zero-violation DRC result never sets `fabrication_authorized` to true — a human review is mandatory.
