# Copy to CIRCUITPY/code.py to verify wiring. Expected output with both
# sensors on the STEMMA QT chain:  ['0x36', '0x47']   (AS5600, BMP585)
import time
import board

i2c = board.STEMMA_I2C()
while not i2c.try_lock():
    pass
try:
    while True:
        found = [hex(a) for a in i2c.scan()]
        print("I2C devices:", found)
        time.sleep(2)
finally:
    i2c.unlock()
