"""Native ARM GCC build from the pinned Seeed STM32CubeIDE LoRaWAN project.

Resolve the vendor .project linked sources and .cproject Debug include/define
contract, build using GNU Arm Embedded + the vendor startup/linker script.
No vendor code is checked into FENG-LABORATORY and no MCU is flashed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from .make_overlay import APP_DIR, prepare_overlay


class BuildError(ValueError):
    pass


def _vendor_root(ide:Path) -> Path:
    # STM32CubeIDE -> LoRaWAN_End_Node -> LoRaWAN -> Applications -> Projects -> Seeed root
    return ide.resolve().parents[4]


def filter_duplicates(paths) -> tuple[Path,...]:
    result=tuple(Path(p).resolve() for p in paths)
    if len(set(result))!=len(result):
        raise BuildError("Duplicate compilation unit in vendor source list")
    return result


def parse_linked_sources(ide: Path) -> tuple[Path,...]:
    ide=ide.resolve()
    root=_vendor_root(ide)
    try:
        project=ET.parse(ide/".project").getroot()
    except (ET.ParseError,OSError) as exc:
        raise BuildError("No valid Seeed STM32CubeIDE .project metadata") from exc
    sources=[]
    for link in project.findall("./linkedResources/link"):
        uri=link.findtext("locationURI","")
        match=re.fullmatch(r"PARENT-([1-5])-PROJECT_LOC/([A-Za-z0-9_./-]+)",uri)
        if not match:
            if uri.endswith((".c",".s",".S")):
                raise BuildError(f"Unsupported vendor source URI: {uri}")
            continue
        if not uri.endswith((".c",".s",".S")):
            continue
        parent_steps=int(match.group(1))
        p=(ide.parents[parent_steps-1]/match.group(2)).resolve()
        if not p.is_relative_to(root) or not p.is_file():
            raise BuildError(f"Vendor source missing or outside official project: {uri}")
        sources.append(p)
    if len(sources)<2:
        raise BuildError("Vendor .project does not expose required source list")
    return filter_duplicates(sources)


def parse_cproject_includes(ide: Path) -> tuple[tuple[Path,...],tuple[str,...]]:
    ide=ide.resolve()
    root=_vendor_root(ide)
    try:
        settings=ET.parse(ide/".cproject").getroot()
    except (ET.ParseError,OSError) as exc:
        raise BuildError("No valid Seeed STM32CubeIDE .cproject metadata") from exc
    config=None
    for cfg in settings.findall(".//cconfiguration"):
        if any(s.get("name")=="Debug" for s in cfg.findall("./storageModule")):
            config=cfg
            break
        if cfg.get("name")=="Debug":
            config=cfg
            break
    if config is None:
        raise BuildError("Debug STM32CubeIDE configuration missing")
    cc=next((tool for tool in config.findall(".//tool")
             if tool.get("name")=="MCU GCC Compiler"),None)
    if cc is None:
        raise BuildError("No MCU GCC Compiler tool options")
    includes,defines=[],[]
    for option in cc.findall("option"):
        tag=option.get("name")
        if tag=="Include paths (-I)":
            for el in option.findall("listOptionValue"):
                relative=el.get("value","")
                if "$" in relative:
                    raise BuildError("Unresolved CubeIDE include-path macro")
                candidate=(ide/"Debug"/relative).resolve()
                if not candidate.is_relative_to(root):
                    raise BuildError("Vendor include path escaped root")
                includes.append(candidate)
        if tag=="Define symbols (-D)":
            defines.extend(el.get("value","") for el in option.findall("listOptionValue"))
    if len(includes)<2 or not {"STM32WLE5xx","CORE_CM4","USE_HAL_DRIVER"}.issubset(defines):
        raise BuildError("Missing mandatory STM32WL includes or compiler definitions")
    for name in defines:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:=[A-Za-z0-9_]+)?",name):
            raise BuildError("Malformed MCU compiler preprocessor definition")
    return tuple(includes),tuple(defines)


def build_image(vendor_root:Path,output_dir:Path, *,execute=subprocess.run) -> dict:
    vendor_root=vendor_root.resolve()
    ide=vendor_root/"Projects/Applications/LoRaWAN/LoRaWAN_End_Node/STM32CubeIDE"
    if not ide.is_dir() or not (ide/"STM32WLE5JCIX_FLASH.ld").is_file():
        raise BuildError("Expected Wio-E5 STM32WLE5JCIX CubeIDE project/linker script")
    sources=list(parse_linked_sources(ide))
    source_dir=ide/"Application/User/Core"
    sources += sorted(source_dir.glob("*.c"))
    sources += sorted((ide/"Application/User/Startup").glob("*.s"))
    sources=list(filter_duplicates(sources))
    if not any(s.name.startswith("startup_stm32wle5jci") for s in sources):
        raise BuildError("Missing STM32WLE5JC startup code")
    includes,defines=parse_cproject_includes(ide)
    if output_dir.exists():
        raise BuildError("Output directory exists; refusing to replace compiled artifacts")
    output_dir.mkdir(parents=True)
    overlay=output_dir/"overlay"
    reference=prepare_overlay(vendor_root,overlay)
    original=(vendor_root/APP_DIR/"lora_app.c").resolve()
    if original not in sources:
        raise BuildError("Vendor project does not reference the LoRaWAN application")
    sources[sources.index(original)]=(overlay/"lora_app.c").resolve()
    sources.append((overlay/"thermo_iot_frame.c").resolve())
    sources=list(filter_duplicates(sources))
    options=[
        "-mcpu=cortex-m4","-mthumb","-mfloat-abi=soft",
        "-ffunction-sections","-fdata-sections","-fno-common",
        "-fno-builtin","-Os","-g3",
    ]
    arguments=[arg for i in includes for arg in ("-I",str(i))]
    arguments=["-I",str(overlay),*arguments,*(f"-D{s}" for s in defines)]
    objects=[]
    object_dir=output_dir/"objects"
    object_dir.mkdir()
    for i,source in enumerate(sources):
        target=object_dir/f"{i:03d}_{source.stem}.o"
        cmd=["arm-none-eabi-gcc",*options,*arguments,"-c",str(source),"-o",str(target)]
        try:
            execute(cmd,check=True)
        except subprocess.CalledProcessError as exc:
            raise BuildError(f"ARM source compile failed: {source.name} (exit {exc.returncode})") from exc
        objects.append(target)
    elf=output_dir/"thermo_wio_e5_rf_reference.elf"
    linker=ide/"STM32WLE5JCIX_FLASH.ld"
    linker_flags=[
        "-specs=nano.specs","-specs=nosys.specs",
        f"-Wl,-Map={output_dir/'thermo_wio_e5_rf_reference.map'}",
        "-Wl,--gc-sections","-Wl,--print-memory-usage",
    ]
    try:
        execute(["arm-none-eabi-gcc",*options,"-T",str(linker),*linker_flags,
                 *(str(o) for o in objects),"-lc","-lm","-lnosys","-o",str(elf)],check=True)
        hexfile=output_dir/"thermo_wio_e5_rf_reference.hex"
        execute(["arm-none-eabi-objcopy","-O","ihex",str(elf),str(hexfile)],check=True)
        execute(["arm-none-eabi-size",str(elf)],check=True)
    except subprocess.CalledProcessError as exc:
        raise BuildError(f"ARM link/objcopy failed (exit {exc.returncode})") from exc
    if not elf.is_file() or not hexfile.is_file() or elf.stat().st_size==0:
        raise BuildError("ARM compiler did not produce non-empty ELF and HEX")
    report={
        "target":"STM32WLE5JCIx",
        "mode":"laboratory_rf_reference_only",
        "files_built":len(sources),
        "payload_port":reference["fport"],
        "firmware_sha256":hashlib.sha256(hexfile.read_bytes()).hexdigest(),
        "output_hex":str(hexfile),
        "output_elf":str(elf),
        "device_flashed":False,
        "real_lorawan_transmission_verified":False,
        "real_teg_power_verified":False,
        "disclaimer":"No physical flash or antenna test; OTA keys and RF compliance need operator inspection.",
    }
    (output_dir/"build-report.json").write_text(json.dumps(report,indent=2))
    return report


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="Build native STM32WLE5JCIx RF reference image")
    p.add_argument("--vendor-root",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        report=build_image(args.vendor_root,args.output_dir)
    except (OSError,BuildError) as exc:
        print(f"Not a flashable build: {exc}",file=sys.stderr)
        return 2
    print(json.dumps(report,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
