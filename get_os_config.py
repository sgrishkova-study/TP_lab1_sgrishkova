import os, platform, socket, json, sys
from pathlib import Path

def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return None

data_dict = {
    "system" : platform.system(), 
    "node" : platform.node(),
    "system_release" : platform.release(),
    "system_version" : platform.version(),
    "platform" : platform.platform(),
    "machine" : platform.machine(),
    "user" : os.getlogin(),
    "has_dualstack_ipv6" : socket.has_dualstack_ipv6(),
    "byteorder" : sys.byteorder,
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
        data_dict.update({key + "_in_bytes" : (int(fields[0]) * 1024) })

    interfaces = {}
    net_dir = Path("/sys/class/net")
    try:
        for interface_dir in sorted(net_dir.iterdir()):
            name = interface_dir.name
            interfaces[name] = {}
            for interface in sorted(interface_dir.iterdir()):
                interfaces[name].update({interface.name : read_text(interface)})
        
        data_dict.update({"net_interfaces" : interfaces})
        
    except OSError:
        pass

    
    

if data_dict['system'] == 'Windows':
    data_dict.update({"windows?": "yes" })
    data_dict.update({"windows_version" : platform.win32_ver(release='', version='', csd='', ptype='')})
    data_dict.update({"windows_edition" : platform.win32_edition()})
    data_dict.update({"windows_is_iot" : platform.win32_is_iot()})


with open("ur_data.json", mode="w", encoding="utf-8") as write_file:
    json.dump(data_dict, write_file)
