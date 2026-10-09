"""Offline contract for reproducible native Wio-E5 GCC linkage source discovery."""
import tempfile
from pathlib import Path
import unittest
from firmware.stm32wle5jc.build_cube_gcc import (
    BuildError, parse_linked_sources, parse_cproject_includes,
    filter_duplicates
)


class CubeGccBuildTests(unittest.TestCase):
    def test_resolves_parent_1_and_parent_5_project_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            vendor=Path(tmp)/"seeed"
            ide=vendor/"Projects/Applications/LoRaWAN/LoRaWAN_End_Node/STM32CubeIDE"
            ide.mkdir(parents=True)
            (vendor/"Utilities").mkdir()
            (vendor/"Utilities/stm32_util.c").write_text("int ok(void){return 0;}")
            (ide.parent/"Core/Src").mkdir(parents=True)
            (ide.parent/"Core/Src/main.c").write_text("void main(void){}")
            (ide/".project").write_text("""<projectDescription><linkedResources>
              <link><name>Utilities/stm32_util.c</name><type>1</type>
                 <locationURI>PARENT-5-PROJECT_LOC/Utilities/stm32_util.c</locationURI></link>
              <link><name>Application/User/Core/main.c</name><type>1</type>
                 <locationURI>PARENT-1-PROJECT_LOC/Core/Src/main.c</locationURI></link>
              </linkedResources></projectDescription>""")
            paths=parse_linked_sources(ide)
            self.assertEqual(len(paths),2)
            self.assertIn(vendor/"Utilities/stm32_util.c",paths)
            self.assertIn(ide.parent/"Core/Src/main.c",paths)

    def test_rejects_repo_escape_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            ide=Path(tmp)/"seeed/Projects/Applications/LoRaWAN/LoRaWAN_End_Node/STM32CubeIDE"
            ide.mkdir()
            (ide/".project").write_text(
                "<projectDescription><linkedResources><link><name>escape.c</name>"
                "<locationURI>PARENT-1-PROJECT_LOC/../../escape.c</locationURI>"
                "</link></linkedResources></projectDescription>"
            )
            with self.assertRaises(BuildError):
                parse_linked_sources(ide)

    def test_parse_compiler_includes_and_definitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            ide=Path(tmp)/"seeed/Projects/Applications/LoRaWAN/LoRaWAN_End_Node/STM32CubeIDE"
            ide.mkdir(parents=True)
            (ide/".cproject").write_text("""<cproject>
              <cconfiguration name="Debug">
                <tool name="MCU GCC Compiler">
                  <option name="Include paths (-I)">
                    <listOptionValue value="../../Core/Inc"/>
                    <listOptionValue value="../../LoRaWAN/App"/>
                  </option>
                  <option name="Define symbols (-D)">
                    <listOptionValue value="CORE_CM4"/>
                    <listOptionValue value="STM32WLE5xx"/>
                    <listOptionValue value="USE_HAL_DRIVER"/>
                  </option>
                </tool>
              </cconfiguration></cproject>""")
            inc,defines=parse_cproject_includes(ide)
            self.assertEqual(defines,("CORE_CM4","STM32WLE5xx","USE_HAL_DRIVER"))
            self.assertEqual(len(inc),2)
            self.assertEqual(inc[0],(ide/"Debug/../../Core/Inc").resolve())

    def test_duplicates_prohibited(self):
        with self.assertRaises(BuildError):
            filter_duplicates((Path("a.c"),Path("a.c")))


if __name__=="__main__":
    unittest.main()
