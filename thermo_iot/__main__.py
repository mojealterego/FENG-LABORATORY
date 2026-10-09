"""CLI for an explicitly hypothetical Thermo-IoT power budget."""

import argparse
from dataclasses import asdict
import json

from .energy import EnergyScenario, evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description="Thermo-IoT: average-power feasibility screening")
    parser.add_argument("--teg-mw", type=float, default=0.1, help="Measured TEG output into PMIC [mW]")
    parser.add_argument("--sleep-uw", type=float, default=8.0, help="Continuous total standby including leakage [uW]")
    parser.add_argument("--efficiency", type=float, default=0.65, help="Electrical conversion efficiency, 0..1")
    parser.add_argument("--cycle-mj", type=float, default=21.9, help="Full measurement + radio cycle [mJ]")
    parser.add_argument("--airtime-s", type=float, default=0.2, help="TX airtime per cycle [s]")
    parser.add_argument("--duty-cycle", type=float, default=0.01, help="Relevant regulatory subband duty-cycle fraction")
    args = parser.parse_args()
    scenario = EnergyScenario(
        teg_power_w=args.teg_mw * 1e-3,
        sleep_power_w=args.sleep_uw * 1e-6,
        efficiency=args.efficiency,
        cycle_energy_j=args.cycle_mj * 1e-3,
        airtime_s=args.airtime_s,
        duty_cycle=args.duty_cycle,
    )
    result = evaluate(scenario)
    print(json.dumps({"scenario": asdict(scenario), "result": asdict(result), "note": "Scenario, not laboratory evidence"}, indent=2))


if __name__ == "__main__":
    main()
