import ctypes
import getpass
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return None


def run_command(command):
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    except (OSError, ValueError):
        return None

    output = (completed.stdout or "").strip()
    return output or None


def safe_get_user():
    for value in (os.environ.get("USER"), os.environ.get("USERNAME")):
        if value:
            return value
    try:
        return getpass.getuser()
    except Exception:
        pass
    try:
        return os.getlogin()
    except OSError:
        return "unknown"


def read_registry_values(winreg_module, path, hive=None, access=0):
    result = {}
    hive_value = hive if hive is not None else winreg_module.HKEY_LOCAL_MACHINE

    try:
        with winreg_module.OpenKey(hive_value, path, 0, winreg_module.KEY_READ | access) as key:
            index = 0
            while True:
                try:
                    name, value, _kind = winreg_module.EnumValue(key, index)
                    result[name] = value
                    index += 1
                except OSError:
                    break
    except OSError:
        pass

    return result


def collect_data():
    data_dict = {
        "system": platform.system(),
        "system_node": platform.node(),
        "system_release": platform.release(),
        "system_version": platform.version(),
        "system_platform": platform.platform(),
        "system_machine": platform.machine(),
        "system_user": safe_get_user(),
        "system_byteorder": sys.byteorder,
        "CPU": platform.processor(),
        "CPU_count": os.cpu_count(),
    }

    if data_dict["system"] == "Linux":
        cpu = read_text("/proc/cpuinfo")
        if cpu:
            for line in cpu.splitlines():
                if line.startswith("vendor_id"):
                    data_dict["CPU_vendor_id"] = line.split(":", 1)[1].strip()
                    continue
                if line.startswith("model name"):
                    data_dict["CPU_model_name"] = line.split(":", 1)[1].strip()
                    continue
                if line.startswith("cache size"):
                    fields = line.split(":", 1)[1].strip().split()
                    if fields and fields[0].isdigit():
                        data_dict["CPU_cache_size_in_bytes"] = int(fields[0]) * 1024
                    continue
                if line.startswith("flags"):
                    data_dict["CPU_flags"] = line.split(":", 1)[1].strip()
                    continue
                if line.startswith("bugs"):
                    data_dict["CPU_bugs"] = line.split(":", 1)[1].strip()
                    continue
                if line.startswith("power management"):
                    break

        mem = read_text("/proc/meminfo")
        if mem:
            for line in mem.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                fields = value.split()
                if not fields:
                    continue
                try:
                    data_dict[f"memory_{key}_in_bytes"] = int(fields[0]) * 1024
                except ValueError:
                    continue

        interfaces = {}
        net_dir = Path("/sys/class/net")
        try:
            for interface_dir in sorted(net_dir.iterdir()):
                name = interface_dir.name
                interfaces[name] = {}

                for folder in interface_dir.iterdir():
                    if folder.is_dir() and folder.name == "device":
                        for file in folder.iterdir():
                            if file.is_file():
                                value = read_text(file)
                                if value is not None:
                                    interfaces[name][f"{name}_interface_{folder.name}_{file.name}"] = value.strip()

                    if folder.is_file():
                        value = read_text(folder)
                        if value is not None:
                            interfaces[name][f"{name}_interface_{folder.name}"] = value.strip()

            data_dict["net_interfaces"] = interfaces
        except OSError:
            pass

        processes = {}
        proc_dir = Path("/proc")
        try:
            for entry in proc_dir.iterdir():
                if entry.name.isdigit():
                    proc_id = entry.name
                    name = read_text(entry / "comm")
                    if name:
                        processes[proc_id] = {"proc_name": name.strip()}

                        status = read_text(entry / "status")
                        if status:
                            for line in status.splitlines():
                                if line.startswith("State"):
                                    processes[proc_id]["proc_state"] = line.split(":", 1)[1].strip()
                                    break
        except OSError:
            pass

        data_dict.update(processes)

    if data_dict["system"] == "Windows":
        try:
            import winreg
        except ImportError:
            winreg = None

        if winreg is not None:
            try:
                data_dict["windows_version"] = platform.win32_ver(release="", version="", csd="", ptype="")
                data_dict["windows_edition"] = platform.win32_edition()
                data_dict["windows_is_iot"] = platform.win32_is_iot()
            except Exception:
                pass

            bios = read_registry_values(winreg, r"HARDWARE\DESCRIPTION\System\BIOS")
            wanted_bios_fields = (
                "SystemManufacturer",
                "SystemProductName",
                "SystemFamily",
                "BIOSVendor",
                "BIOSVersion",
                "BIOSReleaseDate",
            )
            data_dict["system_firmware"] = {
                name: bios[name] for name in wanted_bios_fields if name in bios
            }

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            try:
                memory = MEMORYSTATUSEX()
                memory.dwLength = ctypes.sizeof(memory)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
                    data_dict["memory"] = {
                        "total_bytes": memory.ullTotalPhys,
                        "available_bytes": memory.ullAvailPhys,
                        "memory_load_percent": memory.dwMemoryLoad,
                    }
            except (AttributeError, OSError):
                pass

            apps = {}
            uninstall_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ]

            for path in uninstall_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as root:
                        index = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(root, index)
                                index += 1
                            except OSError:
                                break

                            try:
                                with winreg.OpenKey(root, subkey_name) as app_key:
                                    app = {}
                                    for field in (
                                        "DisplayName",
                                        "DisplayVersion",
                                        "Publisher",
                                        "InstallDate",
                                        "EstimatedSize",
                                    ):
                                        try:
                                            app[field] = winreg.QueryValueEx(app_key, field)[0]
                                        except OSError:
                                            pass
                                    if app.get("DisplayName"):
                                        apps[app["DisplayName"]] = app
                            except OSError:
                                continue
                except OSError:
                    continue

            data_dict["apps"] = apps

    if data_dict["system"] == "Darwin":
        sw_vers = run_command(["sw_vers"])
        if sw_vers:
            macos_version = {}
            for line in sw_vers.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    macos_version[key.strip()] = value.strip()
            if macos_version:
                data_dict["macos_version"] = macos_version

        cpu_brand = run_command(["sysctl", "-n", "machdep.cpu.brand_string"])
        if cpu_brand:
            data_dict["CPU_model_name"] = cpu_brand

        cpu_vendor = run_command(["sysctl", "-n", "machdep.cpu.vendor"])
        if cpu_vendor:
            data_dict["CPU_vendor_id"] = cpu_vendor

        mem_size = run_command(["sysctl", "-n", "hw.memsize"])
        if mem_size and mem_size.isdigit():
            data_dict["memory_MemTotal_in_bytes"] = int(mem_size)

        interfaces = {}
        ifconfig_output = run_command(["ifconfig", "-a"])
        if ifconfig_output:
            current = None
            for line in ifconfig_output.splitlines():
                if line and not line.startswith(("\t", " ")) and ":" in line:
                    current = line.split(":", 1)[0]
                    interfaces[current] = {}
                    continue
                if current and "inet " in line:
                    interfaces[current]["inet"] = line.strip()
            if interfaces:
                data_dict["net_interfaces"] = interfaces

        processes = {}
        ps_output = run_command(["ps", "-axo", "pid=,comm=,state="])
        if ps_output:
            for line in ps_output.splitlines():
                parts = line.strip().split(None, 2)
                if len(parts) >= 2:
                    proc_id = parts[0]
                    proc_name = parts[1]
                    proc_state = parts[2] if len(parts) >= 3 else ""
                    processes[proc_id] = {
                        "proc_name": proc_name,
                        "proc_state": proc_state,
                    }
        data_dict.update(processes)

    return data_dict


def write_data(path="ur_data.json"):
    with open(path, mode="w", encoding="utf-8") as write_file:
        json.dump(collect_data(), write_file)


def main():
    write_data()


if __name__ == "__main__":
    main()
