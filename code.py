"""
PyPortal Weather Station
==============================================
Turn your PyPortal into a weatherstation with
Adafruit IO

Author: Brent Rubell for Adafruit Industries, 2019
"""
import time
import board
import neopixel
import busio
import analogio
from simpleio import map_range
from digitalio import DigitalInOut

from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

import adafruit_bme280
import weatherstation_helper

PYPORTAL_REFRESH = 30

# anemometer defaults
anemometer_min_volts = 0.4
anemometer_max_volts = 2.0
min_wind_speed = 0.0
max_wind_speed = 32.4

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# PyPortal ESP32 Setup
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

ADAFRUIT_IO_USER = secrets['aio_username']
ADAFRUIT_IO_KEY = secrets['aio_key']

io = IO_HTTP(ADAFRUIT_IO_USER, ADAFRUIT_IO_KEY, wifi)

i2c = busio.I2C(board.SCL, board.SDA)

bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

bme280.sea_level_pressure = 1013.25
# init. the graphics helper
gfx = weatherstation_helper.WeatherStation_GFX()
uv_index = 10
sgp_data = 1

adc = analogio.AnalogIn(board.D4)

print('Getting Group data from Adafruit IO...')
station_group = io.get_group('weatherstation')
feed_list = station_group['feeds']
temperature_feed = feed_list[0]
pressure_feed =    feed_list[1]
wind_speed_feed =  feed_list[2]

def adc_to_wind_speed(val):
    voltage_val = val / 65535 * 3.3
    voltage_val = voltage_val * 2.237
    return map_range(voltage_val, 0.4, 2, 0, 32.4)

def send_to_io():
    io.send_data(wind_speed_feed['key'], wind_speed)
    io.send_data(temperature_feed['key'], bme280_data[0])
    io.send_data(pressure_feed['key'], bme280_data[2])

while True:
    bme280_data = [bme280.temperature, bme280.pressure]
    wind_speed = adc_to_wind_speed(adc.value)

    print('displaying sensor data...')
    gfx.display_data(bme280_data, wind_speed)

    print('sensor data displayed!')
    try:
        try:
            print('Sending data to Adafruit ')
            gfx.display_io_status('Sending data ')
            send_to_io()
            gfx.display_io_status('Data Sent ')
            print('Data sent !')
        except AdafruitIO_RequestError as e:
            raise AdafruitIO_RequestError('IO Error: ', e)
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    time.sleep(PYPORTAL_REFRESH)

