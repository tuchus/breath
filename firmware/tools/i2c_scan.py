# Copy to CIRCUITPY/code.py to verify wiring. Expected output with the
# BMP585 connected:  ['0x47']
# On a Pico, set the pins the sensor is wired to:
I2C_SDA = "GP4"
I2C_SCL = "GP5"

import time
import board


def open_i2c():
    if hasattr(board, "STEMMA_I2C"):
        return board.STEMMA_I2C()
    import busio

    return busio.I2C(getattr(board, I2C_SCL), getattr(board, I2C_SDA))


i2c = open_i2c()
while not i2c.try_lock():
    pass
try:
    while True:
        found = [hex(a) for a in i2c.scan()]
        print("I2C devices:", found)
        time.sleep(2)
finally:
    i2c.unlock()
