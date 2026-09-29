import json
import os
import platform
import sys
from pathlib import Path


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return None

data_dict = {
    "system" : platform.system(), 
    "system_node" : platform.node(),
    "system_release" : platform.release(),
    "system_version" : platform.version(),
    "system_platform" : platform.platform(),
    "system_machine" : platform.machine(),
    "system_user" : os.getlogin(),
    "system_byteorder" : sys.byteorder,
    "CPU" : platform.processor(),
    "CPU_count" : os.cpu_count(),
    }

if (data_dict['system'] == 'Linux'):
    cpu = read_text("/proc/cpuinfo")
    for line in cpu.splitlines():
        if line.startswith("vendor_id"):
            data_dict.update({"CPU_vendor_id": line.split(":", 1)[1].strip()})
            continue
        
        if line.startswith("model name"):
            data_dict.update({"CPU_model_name": line.split(":", 1)[1].strip()})
            continue

        if line.startswith("cache size"):
            data_dict.update({"CPU_cache_size_in_bytes": int(line.split(":", 1)[1].strip().split()[0]) * 1024})
            continue
        
        if line.startswith("flags"):
            data_dict.update({"CPU_flags": line.split(":", 1)[1].strip()})
            continue

        if line.startswith("bugs"):
            data_dict.update({"CPU_bugs": line.split(":", 1)[1].strip()})
            continue

        if line.startswith("power managment"):
            break

    mem = read_text("/proc/meminfo")
    for line in mem.splitlines():
        if ":" not in line: continue
        key, value = line.split(":", 1)
        fields = value.split()
        data_dict.update({"memory_" + key + "_in_bytes" : (int(fields[0]) * 1024) })

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
    data_dict.update({"windows?": "yes" })
    data_dict.update({"windows_version" : platform.win32_ver(release='', version='', csd='', ptype='')})
    data_dict.update({"windows_edition" : platform.win32_edition()})
    data_dict.update({"windows_is_iot" : platform.win32_is_iot()})


with open("ur_data.json", mode="w", encoding="utf-8") as write_file:
    json.dump(data_dict, write_file)
