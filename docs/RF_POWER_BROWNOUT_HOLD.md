# Thermo-IoT — LTC3108 / STM32WLE5 RF power integrity HOLD (9 October 2026)

**Status: NO-GO for powering an 87 mA radio pulse from the existing C6 = 470 µF VOUT reservoir.** This is a **public, textbook first-order screening calculation**, not a newly disclosed invention, approved replacement circuit, prototype test, verified radio-current trace, patent claim, or final BOM.

© 2026 Mojeaterego — Andrzej Mikulski. All rights reserved. Kontakt: mojealterego21@gmail.com · +48 455 575 337.

## Existing public candidate and electrical limitations

The LTC3108EGN breakout in `hardware/active_power/` shows C6 = 470 µF on **VOUT (3.3 V nominal)** and a separate **VSTORE (up to about 5.25 V)** connector for storage. Direct VSTORE-to-STM32WLE VDD connection is outside the allowed normal operating voltage of STM32WL. The VOUT2 switched output also does not create more energy. The device VOUT current capability is in the milliampere range under specified conditions, not a guaranteed radio-pulse current.

See [Analog Devices LTC3108, Rev. D](https://www.analog.com/media/en/technical-documentation/data-sheets/LTC3108.pdf) and [STM32WLE5 datasheet](https://www.st.com/resource/en/datasheet/stm32wle5jc.pdf). All measurements, conditions and thermal derating must be validated from the selected components' current manufacturer revisions.

## Conservative charge accounting, 200 ms example

Assumptions **not measured**: initial VOUT = 3.3 V, minimum MCU VDD = 2.0 V (engineering choice, not guaranteed radio spec), TX = 87 mA × 200 ms, RX = 4.82 mA × 1 s, ESR = 0.15 Ω, and **optimistic constant available PMIC current 4.5 mA**. Start voltage, TX currents, ESR, receiver windows and available PMIC current have not been validated on the real board. The model ignores all other startup/rejoin/retries, sensor current, RF duty-cycle variation, capacitor tolerance, cap leak and cold-chain energy.

The charge needed from the **output capacitor**, even with ideal instantaneous source-current contribution, is:

```text
Qout = max(0, ITX - Ipmic) * tTX + max(0, IRX - Ipmic) * tRX
     = (0.087 - 0.0045) * 0.2 + (0.00482 - 0.0045) * 1
     = 0.01682 C

Instantaneous ESR loss = 0.0825 A * 0.15 ohm = 0.012375 V
Available sag budget = 3.3 - 2.0 - 0.012375 = 1.287625 V
Minimum ideal capacitance = 0.01682 C / 1.287625 V
                          ≈ 0.01306 F = 13.1 mF
```

By comparison **470 µF = 0.00047 F**, roughly **28× smaller** than this permissive first-order requirement. The formula `ΔV = Q/C` would exceed the available supply; the physical circuit instead browns out or the regulator/source behavior changes. It is not meaningful to extrapolate a negative VDD as a measured result.

With **no guaranteed PMIC replenishment** during the burst, the ideal charge requirement rises; actual design requirements also depend on retries, vendor parameter conditions, switch resistance, bulk capacitor ESR/temperature, regulator energy transfer and low-voltage cutoff. The generic simulation's default **2.5 F** capacitor is **not** the physical C6 component: it MUST NOT be cited as verification of this PCB.

## Reproducible CLI

```bash
python -m thermo_iot.harvester_rail --capacitance-uf 470 --esr-ohm 0.15 --pmic-current-ma 4.5
# Nonzero exit code 3 and status NO_GO are EXPECTED. This is a protective result.

python -m thermo_iot.power_gate
# Alternative stricter capacitor-only power budget, expect decision HOLD.
```

`thermo_iot.harvester_rail` explicitly exposes the optimistic PMIC current assumption and reports `physical_validation_performed=false`, `fabrication_authorized=false` in either mathematical outcome. A `MODEL_ONLY_PASS` requires laboratory qualification and independent review; it is NEVER hardware acceptance.

## Required next measurements and decisions

1. Obtain **manufacturer-qualified VOUT / VLDO / VSTORE** electrical limits, startup/clamp/load curves, capacitor leakage/ESR vs temperature and source mechanical BOM. Verify the manufacturer-referenced transformer winding polarity; never guess.
2. Characterize the actual Wio-E5 profile with a suitable high-bandwidth current analyzer and oscilloscope: wake, ADC, join, transmission at multiple spreading factors/power levels, RX1/RX2, retries, duty cycle, STOP current. Keep measurement records private pending patent review.
3. Measure the complete PMIC output/storage droop, recharge time, cold-start, TEG hot/cold temperatures, thermal gradients and brownout resets during repeated uplinks. Do not interpret a simulated 4.5 mA as guaranteed current.
4. Reconcile the **actual energy-storage and power-path design** with IP/legal controls *before* publishing a new topology or production CAD. The presently public reference PCB remains **HOLD / NOT FOR FABRICATION** with unrouted copper and unqualified footprints.
5. After independent DRC/ERC, PCB assembly and physical tests, record private, SHA-256-bound evidence and signed engineering GO/NO-GO. No lab measurements, patent clearance, radio transmission or field readiness are claimed by this document.
