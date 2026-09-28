import os, platform, socket, json, pwd


data_dict = {
    "system" : platform.system(), 
    "node" : platform.node(),
    "system_release" : platform.release(),
    "system_version" : platform.version(),
    "platform" : platform.platform(),
    "CPU" : platform.processor(),
    "system_count_CPU" : os.cpu_count(),
    "machine" : platform.machine(),
    "user" : os.getlogin(),
    "has_dualstack_ipv6" : socket.has_dualstack_ipv6(),
    }

if data_dict['system'] == 'Linux':
    for password in pwd.getpwall():
        data_dict.update({"password_path_" + str(password.pw_name) : [password.pw_uid, password.pw_gid, password.pw_dir, password.pw_shell ]})


## print(socket.if_nameindex())

## for windows
##print(platform.win32_ver(release='', version='', csd='', ptype=''))
##print(platform.win32_edition())
##print(platform.win32_is_iot())

with open("ur_data.json", mode="w", encoding="utf-8") as write_file:
    json.dump(data_dict, write_file)
