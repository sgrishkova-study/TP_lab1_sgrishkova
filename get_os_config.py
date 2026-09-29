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
    "CPU" : platform.processor(),
    "CPU_count" : os.cpu_count(),
    "machine" : platform.machine(),
    "user" : os.getlogin(),
    "has_dualstack_ipv6" : socket.has_dualstack_ipv6(),
    "byteorder" : sys.byteorder,
    }

if (data_dict['system'] == 'Linux'):
    mem = read_text("/proc/meminfo")
    for line in mem.splitlines():
        if ":" not in line: continue
        key, value = line.split(":", 1)
        fields = value.split()
        data_dict.update({key + "_in_bytes" : (int(fields[0]) * 1024) })       

if data_dict['system'] == 'Windows':
    data_dict.update({"windows?": "yes" })
    data_dict.update({"windows_version" : platform.win32_ver(release='', version='', csd='', ptype='')})
    data_dict.update({"windows_edition" : platform.win32_edition()})
    data_dict.update({"windows_is_iot" : platform.win32_is_iot()})

with open("ur_data.json", mode="w", encoding="utf-8") as write_file:
    json.dump(data_dict, write_file)
