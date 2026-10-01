import json
import os
import platform
import sys
from pathlib import Path

def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return ""

def read_registry_values(winreg, path, hive, access=0):
    result = {}

    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | access) as key:
            index = 0
            while True:
                try:
                    name, value, _kind = winreg.EnumValue(key, index)
                    result[name] = value
                    index += 1
                except OSError:
                    break
    except OSError:
        pass
    return result

try:
    system_user = os.getlogin()
except OSError:
    system_user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"

data_dict = {
    "system" : platform.system(), 
    "system_node" : platform.node(),
    "system_release" : platform.release(),
    "system_version" : platform.version(),
    "system_platform" : platform.platform(),
    "system_machine" : platform.machine(),
    "system_user" : system_user,
    "system_byteorder" : sys.byteorder,
    "CPU" : platform.processor(),
    "CPU_count" : os.cpu_count(),
    }

if (data_dict['system'] == 'Linux'):
    cpu = read_text("/proc/cpuinfo")

    for line in cpu.splitlines():
        if ":" not in line: continue

        key, value = line.split(":", 1)
        value = value.strip()

        if key == "vendor_id": data_dict["CPU_vendor_id"] = value
        elif key == "model name": 
            data_dict["CPU_model_name"] = value
            continue
        elif key == "cache size": 
            try:
                cache_value, cache_unit = value.split()
                if cache_unit.lower() == "kb":
                    multiplier = 1024
                elif cache_unit.lower() == "mb":
                    multiplier = 1024 ** 2
                else:
                    multiplier = 1

                data_dict["CPU_cache_size_in_bytes"] = int(cache_value) * multiplier
            except ValueError:
                pass
        elif key == "flags": data_dict["CPU_flags"] = value
        elif key == "bugs": data_dict["CPU_bugs"] = value
        elif key == "power management": break

    mem = read_text("/proc/meminfo")
    memory = {}

    for line in mem.splitlines():
        if ":" not in line: continue

        key, value = line.split(":", 1)
        fields = value.split()
        if not fields: continue

        try:
            number = int(fields[0])
            unit = fields[1].lower()

            if unit == "kb":
                number *= 1024
            elif unit == "mb":
                number *= 1024 ** 2
            
            memory[key.strip() + "_in_bytes"] = number
        except ValueError:
            continue
    
        data_dict["memory"] = memory

    interfaces = {}
    net_dir = Path("/sys/class/net")

    try:
        for interface_dir in sorted(net_dir.iterdir()):
            name = interface_dir.name
            interfaces[name] = {}

            for folder in interface_dir.iterdir():
                if folder.is_dir() and (folder.name == "device"):
                    for file in folder.iterdir():
                        if file.is_file():
                            interfaces[name].update({ name + "_interface_" + folder.name + "_" + file.name : read_text(file)})
                
                if folder.is_file():
                    interfaces[name].update({name + "_interface_" + folder.name : read_text(folder)})
        
        data_dict.update({"net_interfaces" : interfaces})
        
    except OSError:
        pass

    processes = {}
    proc_dir = Path("/proc")
    try:
        for entry in proc_dir.iterdir():
            if entry.name.isdigit():
                proc_id = int(entry.name)
                name = read_text(entry / "comm")
                if name:
                    processes[proc_id] = {}
                    processes[proc_id].update({"proc_name" : name.strip()})
                
                    status = read_text(entry / "status")
                    for line in status.splitlines():
                        if line.startswith("State"):
                            processes[proc_id].update({"proc_state" : line.split(":", 1)[1].strip()})
                            break 
    except OSError:
        pass

    data_dict.update(processes)
    
    

if data_dict['system'] == 'Windows':
    import ctypes
    import winreg

    data_dict["windows_version"] = platform.win32_ver(release="", version="", csd="", ptype="")
    data_dict["windows_edition"] = platform.win32_edition()
    data_dict["windows_is_iot"] = platform.win32_is_iot()

    bios = read_registry_values(winreg, r"HARDWARE\DESCRIPTION\System\BIOS", winreg.HKEY_LOCAL_MACHINE)
    wanted_bios_fields = (
        "SystemManufacturer",
        "SystemProductName",
        "SystemFamily",
        "SystemSKUNumber",
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

    results = {}
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
                                results[app.get("DisplayName")] = app
                    except OSError:
                        continue
        except OSError:
            continue

    data_dict["apps"] = results


with open("ur_data.json", mode="w", encoding="utf-8") as write_file:
    json.dump(data_dict, write_file, indent=2, ensure_ascii=False)
