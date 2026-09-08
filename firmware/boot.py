# boot.py runs once at power-up, before code.py.
# Rename the USB device so it shows up as "Breath Controller" in your DAW's
# MIDI device list instead of "QT Py RP2040". Requires CircuitPython 8+.
import supervisor

supervisor.set_usb_identification(manufacturer="tuchus", product="Breath Controller")
