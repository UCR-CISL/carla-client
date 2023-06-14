import evdev
from evdev import ecodes, InputDevice

device = evdev.list_devices()[0]
print(device)
evtdev = InputDevice(device)
val = 0  # val \in [0,65535]
evtdev.write(ecodes.EV_FF, ecodes.FF_AUTOCENTER, val)
