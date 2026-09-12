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
from adafruit_register.register_bit import ROBit

import tuning
from breath import BreathMapper

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

LIVE_TUNING = True        # accept tuning CCs from tools/bench.html on channel 16

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
class BMP(adafruit_bmp5xx.BMP5XX):
    # OSR_EFF register (0x38) bit 7: the sensor sets this when the requested
    # output data rate is achievable at the requested oversampling.
    odr_is_valid = ROBit(0x38, 7)


# Fastest first; the sensor tells us which of these it can actually do at
# the chosen oversampling, so we don't have to hard-code Bosch's table.
_ODR_CANDIDATES = (
    ("140 Hz", adafruit_bmp5xx.BMP5XX_ODR_140_HZ),
    ("120 Hz", adafruit_bmp5xx.BMP5XX_ODR_120_HZ),
    ("100 Hz", adafruit_bmp5xx.BMP5XX_ODR_100_2_HZ),
    ("80 Hz", adafruit_bmp5xx.BMP5XX_ODR_80_HZ),
    ("60 Hz", adafruit_bmp5xx.BMP5XX_ODR_60_HZ),
    ("50 Hz", adafruit_bmp5xx.BMP5XX_ODR_50_HZ),
)


def configure_sensor(sensor):
    """Low oversampling, fastest valid data rate, light IIR smoothing.

    The driver defaults to 16x oversampling at 50 Hz, tuned for altimetry.
    Breath is a large signal (hundreds of Pa) so 4x is plenty of resolution
    and lets the sensor run much faster.
    """
    sensor.mode = adafruit_bmp5xx.BMP5XX_POWERMODE_STANDBY
    sensor.pressure_oversampling_rate = adafruit_bmp5xx.BMP5XX_OVERSAMPLING_4X
    sensor.temperature_oversampling_rate = adafruit_bmp5xx.BMP5XX_OVERSAMPLING_1X
    sensor.pressure_iir_filter = adafruit_bmp5xx.BMP5XX_IIR_FILTER_COEFF_3
    for name, odr in _ODR_CANDIDATES:
        sensor.output_data_rate = odr
        sensor.mode = adafruit_bmp5xx.BMP5XX_POWERMODE_NORMAL
        time.sleep(0.01)
        if sensor.odr_is_valid:
            print("BMP585 running at", name)
            return
        sensor.mode = adafruit_bmp5xx.BMP5XX_POWERMODE_STANDBY
    print("BMP585: no candidate ODR reported valid, using driver default 50 Hz")
    sensor.output_data_rate = adafruit_bmp5xx.BMP5XX_ODR_50_HZ
    sensor.mode = adafruit_bmp5xx.BMP5XX_POWERMODE_NORMAL


bmp = BMP.over_i2c(i2c)
configure_sensor(bmp)

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
midi_in = usb_midi.ports[0]
midi_out = usb_midi.ports[1]
_cc_buf = bytearray(3)


def send_cc(cc, value, channel=MIDI_CHANNEL):
    _cc_buf[0] = 0xB0 | channel
    _cc_buf[1] = cc
    _cc_buf[2] = value & 0x7F
    midi_out.write(_cc_buf)


def send_settings(m):
    for cc, value in tuning.report(m):
        send_cc(cc, value, tuning.TUNE_CHANNEL)


cc_parser = tuning.ControlChangeParser()


# --- Ambient baseline -------------------------------------------------------
def measure_baseline(seconds):
    print("Measuring ambient pressure for %.1fs, don't blow..." % seconds)
    n, total = 0, 0.0
    t_end = time.monotonic() + seconds
    while time.monotonic() < t_end:
        if bmp.data_ready:
            total += bmp.pressure
            n += 1
    result = total / max(n, 1)
    print("baseline %.2f hPa (%d samples)" % (result, n))
    return result


baseline = measure_baseline(BASELINE_SECONDS)

mapper = BreathMapper(
    threshold=THRESHOLD_HPA,
    full_scale=FULL_SCALE_HPA,
    curve=CURVE,
    smoothing=SMOOTHING,
    baseline_track=BASELINE_TRACK,
    bits=14 if SEND_14BIT else 7,
)
mapper.set_baseline(baseline)
if pixel:
    pixel.fill((0, 40, 0))

# --- Main loop --------------------------------------------------------------
last_debug = time.monotonic()

send_cc(BREATH_CC, 0)
if SEND_14BIT:
    send_cc(BREATH_CC_LSB, 0)
if LIVE_TUNING:
    send_settings(mapper)

while True:
    if LIVE_TUNING:
        data = midi_in.read(64)
        if data:
            for channel, cc, value in cc_parser.feed(data):
                if channel != tuning.TUNE_CHANNEL:
                    continue
                action = tuning.apply(mapper, cc, value)
                if action == "rezero":
                    mapper.set_baseline(measure_baseline(BASELINE_SECONDS))
                    send_cc(BREATH_CC, 0)
                    mapper.value = 0
                elif action == "report":
                    send_settings(mapper)
                elif action:
                    print(tuning.settings_text(mapper).replace("\n", "  "))
                    send_settings(mapper)

    if bmp.data_ready:
        value = mapper.update(bmp.pressure)
        if value is not None:
            send_cc(BREATH_CC, mapper.msb)
            if SEND_14BIT:
                send_cc(BREATH_CC_LSB, mapper.lsb)

            if pixel:
                level = mapper.value * 255 // mapper.max_value
                pixel.fill((level, 0, 40 - level * 40 // 255))
            elif led is not None:
                led.value = value > 0

    if DEBUG:
        now = time.monotonic()
        if now - last_debug > 0.1:
            last_debug = now
            print(
                "delta=%6.2f hPa  smoothed=%6.2f  cc=%d"
                % (mapper.delta, mapper.smoothed, mapper.value)
            )
