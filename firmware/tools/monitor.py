# Copy to CIRCUITPY/code.py and open the serial console (Mu, tio, screen...).
# Prints raw sensor values ~20x/sec so you can pick THRESHOLD_HPA and
# FULL_SCALE_HPA for code.py: watch the "delta" column while you blow gently,
# then as hard as you'd ever play.
import time
import board
import adafruit_bmp5xx

i2c = board.STEMMA_I2C()
bmp = adafruit_bmp5xx.BMP5XX.over_i2c(i2c)

try:
    import adafruit_as5600
    mag = adafruit_as5600.AS5600(i2c)
except (ImportError, ValueError):
    mag = None

# 1 s ambient baseline
n, total = 0, 0.0
t_end = time.monotonic() + 1.0
while time.monotonic() < t_end:
    total += bmp.pressure
    n += 1
baseline = total / n
print("baseline %.2f hPa from %d samples" % (baseline, n))

peak = 0.0
while True:
    temp_c, p = bmp.measurements
    delta = p - baseline
    peak = max(peak, delta)
    line = "p=%8.2f hPa  delta=%7.2f hPa  peak=%6.2f  T=%.1fC" % (p, delta, peak, temp_c)
    if mag is not None:
        line += "  angle=%4d/4095 magnet=%s" % (mag.raw_angle, mag.magnet_detected)
    print(line)
    time.sleep(0.05)
