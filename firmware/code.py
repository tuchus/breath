"""USB MIDI breath controller for the Adafruit QT Py RP2040.

Sensor:  BMP585 (I2C address 0x47)

Runs unchanged on the QT Py RP2040 (STEMMA QT socket) or on a Raspberry Pi
Pico / Pico 2 / Pico W / Pico 2 W (sensor wired to the pins in I2C_SDA /
I2C_SCL below).

The BMP585 barometric sensor, ported version, sits at the end of a tube from
the mouthpiece.  Blowing raises the pressure above ambient; that delta is
mapped to MIDI CC 2 (Breath Controller).

Copy this file plus the libraries listed in ../README.md to CIRCUITPY/.
Tune the constants in the TUNING section; use tools/monitor.py to pick them.
"""

import time

import board
import usb_midi
import adafruit_bmp5xx

# --------------------------------------------------------------------------
# TUNING
# --------------------------------------------------------------------------
MIDI_CHANNEL = 0          # 0-based, so 0 == MIDI channel 1
BREATH_CC = 2             # CC 2 = Breath Controller (MSB)
BREATH_CC_LSB = 34        # CC 34 = Breath Controller LSB (only if SEND_14BIT)
SEND_14BIT = False        # True sends CC2 + CC34 for 16384 steps instead of 128

THRESHOLD_HPA = 0.5       # dead zone above ambient before CC rises (≈50 Pa)
FULL_SCALE_HPA = 25.0     # delta that gives CC 127 (≈2.5 kPa, a firm blow)
CURVE = 0.7               # <1 = more sensitive at the quiet end, 1 = linear
SMOOTHING = 0.35          # 0..1, weight of the newest sample (1 = no smoothing)
BASELINE_TRACK = 0.001    # how fast the ambient baseline follows slow drift
BASELINE_SECONDS = 1.0    # ambient averaging time at boot (don't blow!)

I2C_SDA = "GP4"           # Pico only: pins the BMP585 is wired to. Any I2C
I2C_SCL = "GP5"           # pair works (GP4/GP5, GP6/GP7, GP8/GP9, ...).

DEBUG = False             # print pressure/CC to the serial console ~10x/sec
# --------------------------------------------------------------------------


def open_i2c():
    """STEMMA QT socket if the board has one, otherwise the pins above."""
    if hasattr(board, "STEMMA_I2C"):
        return board.STEMMA_I2C()
    import busio

    return busio.I2C(getattr(board, I2C_SCL), getattr(board, I2C_SDA))


i2c = open_i2c()

# --- BMP585 -----------------------------------------------------------------
bmp = adafruit_bmp5xx.BMP5XX.over_i2c(i2c)
# Reconfigure for speed: the driver defaults to 16x oversampling at 50 Hz,
# which is tuned for altimetry. Breath is a large signal (hundreds of Pa), so
# low oversampling is plenty and lets the sensor run at 140 Hz.
bmp.mode = adafruit_bmp5xx.BMP5XX_POWERMODE_STANDBY
bmp.pressure_oversampling_rate = adafruit_bmp5xx.BMP5XX_OVERSAMPLING_4X
bmp.temperature_oversampling_rate = adafruit_bmp5xx.BMP5XX_OVERSAMPLING_1X
bmp.pressure_iir_filter = adafruit_bmp5xx.BMP5XX_IIR_FILTER_COEFF_3
bmp.output_data_rate = adafruit_bmp5xx.BMP5XX_ODR_140_HZ
bmp.mode = adafruit_bmp5xx.BMP5XX_POWERMODE_NORMAL

# --- LED feedback (optional) ------------------------------------------------
# QT Py: onboard NeoPixel shows the breath level. Pico: plain LED lights while
# blowing above the threshold.
pixel = None
led = None
try:
    import neopixel

    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3, auto_write=True)
    pixel.fill((0, 0, 40))
except (ImportError, AttributeError):
    try:
        import digitalio

        led = digitalio.DigitalInOut(board.LED)
        led.direction = digitalio.Direction.OUTPUT
    except (ImportError, AttributeError):
        pass

# --- MIDI -------------------------------------------------------------------
midi_out = usb_midi.ports[1]
_cc_buf = bytearray(3)


def send_cc(cc, value):
    _cc_buf[0] = 0xB0 | MIDI_CHANNEL
    _cc_buf[1] = cc
    _cc_buf[2] = value & 0x7F
    midi_out.write(_cc_buf)


def clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


# --- Ambient baseline -------------------------------------------------------
print("Measuring ambient pressure for %.1fs, don't blow..." % BASELINE_SECONDS)
n, total = 0, 0.0
t_end = time.monotonic() + BASELINE_SECONDS
while time.monotonic() < t_end:
    if bmp.data_ready:
        total += bmp.pressure
        n += 1
baseline = total / max(n, 1)
print("baseline %.2f hPa (%d samples)" % (baseline, n))
if pixel:
    pixel.fill((0, 40, 0))

# --- Main loop --------------------------------------------------------------
smoothed = 0.0
delta = 0.0
last_breath = -1
last_debug = time.monotonic()
span = FULL_SCALE_HPA - THRESHOLD_HPA

send_cc(BREATH_CC, 0)
if SEND_14BIT:
    send_cc(BREATH_CC_LSB, 0)

while True:
    if bmp.data_ready:
        pressure = bmp.pressure
        delta = pressure - baseline

        # Track slow ambient drift only while the player is not blowing.
        if delta < THRESHOLD_HPA:
            baseline += BASELINE_TRACK * delta

        smoothed += SMOOTHING * (delta - smoothed)

        norm = clamp01((smoothed - THRESHOLD_HPA) / span)
        shaped = norm ** CURVE if norm > 0.0 else 0.0

        if SEND_14BIT:
            value = int(shaped * 16383 + 0.5)
            if value != last_breath:
                send_cc(BREATH_CC, value >> 7)
                send_cc(BREATH_CC_LSB, value & 0x7F)
                last_breath = value
        else:
            value = int(shaped * 127 + 0.5)
            if value != last_breath:
                send_cc(BREATH_CC, value)
                last_breath = value

        if pixel:
            level = int(shaped * 255)
            pixel.fill((level, 0, 40 - level * 40 // 255))
        elif led is not None:
            led.value = value > 0

    if DEBUG:
        now = time.monotonic()
        if now - last_debug > 0.1:
            last_debug = now
            print(
                "delta=%6.2f hPa  smoothed=%6.2f  cc=%d"
                % (delta, smoothed, last_breath)
            )
