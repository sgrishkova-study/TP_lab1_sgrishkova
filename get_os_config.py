import platform
import os

print(platform.system())
print(platform.machine())
print(platform.node())
print(platform.platform())
print(platform.processor())
print(platform.release())
print(platform.version())
print(platform.uname())

print(os.getlogin())
print(os.cpu_count())

## for windows
print(platform.win32_ver(release='', version='', csd='', ptype=''))
print(platform.win32_edition())
print(platform.win32_is_iot())

##for linux 
print(platform.freedesktop_os_release())

