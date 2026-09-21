import os, platform, socket, json

data_dict = {
    "system" : platform.system(), 
    "node" : platform.node(),
    "SYSrelease" : platform.release(),
    "SYSversion" : platform.version(),
    "platform" : platform.platform(),
    "CPU" : platform.processor(),
    "SYScountCPU" : os.cpu_count(),
    "machine" : platform.machine(),
    "userSYSlogin" : os.getlogin(),
    "has_dualstack_ipv6" : socket.has_dualstack_ipv6(),
    }

with open("ur_data.json", mode="w", encoding="utf-8") as write_file:
    json.dump(data_dict, write_file)

## print(socket.if_nameindex())

## for windows
print(platform.win32_ver(release='', version='', csd='', ptype=''))
print(platform.win32_edition())
print(platform.win32_is_iot())

