import nidaqmx
system = nidaqmx.system.System.local()
devices = system.devices

print(system.driver_version)
print("Devices: ", [d for d in devices])
