"""PMIC acquisition and energy integration must not claim system efficiency."""
import tempfile
from pathlib import Path
import unittest
from thermo_iot.pmic import (
    PmicPoint, analyze_pmic, capture_scpi, read_pmic_csv,
    save_csv_exclusive, PmicValidationError
)


class DummyMeter:
    def __init__(self,v):
        self.v=v
        self.commands=[]
    def query(self,command):
        self.commands.append(command)
        return str(self.v)


class PmicTests(unittest.TestCase):
    def test_observed_cold_start_and_sample_hold_electrical_power(self):
        sample=(
            PmicPoint(0,0.1,0.002,0,0,0),
            PmicPoint(10,0.1,0.002,3.3,0.001,3.1),
            PmicPoint(20,0.1,0.002,3.3,0.001,3.3),
        )
        report=analyze_pmic(sample,"synthetic")
        self.assertEqual(report["time_to_store_target_s"],10)
        self.assertEqual(report["cold_start_state"],"reached_target")
        self.assertAlmostEqual(report["input_electrical_energy_j"],0.004)
        self.assertAlmostEqual(report["output_electrical_energy_j"],0.033)

    def test_nonempty_initial_buffer_cannot_claim_cold_start(self):
        samples=(PmicPoint(0,0,0,3.3,0.001,3.2),PmicPoint(1,0,0,3.3,0.001,3.3))
        self.assertEqual(analyze_pmic(samples,"measured")["cold_start_state"],
                         "not_observed_initially_discharged")

    def test_capture_real_instrument_api_excludes_fake_efficiency(self):
        meters=[DummyMeter(v) for v in (0.1,0.002,3.3,0.001,3.2)]
        now=iter((1.0,2.0,3.0))
        records=capture_scpi(meters,steps=2,interval_s=0.1,monotonic=lambda:next(now),
                             sleep=lambda _:None)
        self.assertEqual(records[0]["evidence_type"],"measured")
        self.assertEqual(records[0]["vstore_v"],3.2)
        self.assertEqual(len(meters[0].commands),2)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"pmic.csv"
            save_csv_exclusive(path,records)
            evidence,points=read_pmic_csv(path)
            self.assertEqual(evidence,"measured")
            self.assertEqual(len(points),2)
            with self.assertRaises(FileExistsError):
                save_csv_exclusive(path,records)

    def test_rejects_duplicate_resources_mixed_sources_and_invalids(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"profile.csv"
            path.write_text(
                "elapsed_s,vin_v,iin_a,vout_v,iout_a,vstore_v,evidence_type\n"
                "0,0.1,0.1,3.3,0.1,1,synthetic\n"
                "1,0.2,0.1,3.3,0.1,2,measured\n",encoding="utf-8")
            with self.assertRaises(PmicValidationError):
                read_pmic_csv(path)
        for data in ((PmicPoint(0,float("nan"),0,0,0,0), PmicPoint(1,0,0,0,0,0)),):
            with self.assertRaises(PmicValidationError):
                analyze_pmic(data,"synthetic",start_v=0.1,target_v=3)
        with self.assertRaises(PmicValidationError):
            capture_scpi([],steps=2,interval_s=1)


if __name__=="__main__":
    unittest.main()
