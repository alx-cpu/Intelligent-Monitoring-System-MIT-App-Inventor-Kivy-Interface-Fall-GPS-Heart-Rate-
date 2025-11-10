import time
import ctypes as ct
import numpy as np
from scipy import signal
import pigpio
import math
import threading


class ADXL345:
    """ Class for interfacing with the ADXL345 accelerometer and implementing fall detection logic using SPI."""
    def __init__(self, sample_rate=10):
        """ Initializes the ADXL345 sensor registers and configures SPI communication. """
        # register addresses for ADXL345
        self.DATA_FORMAT = 0x31
        self.DATA_FORMAT_B = 0x0b
        self.READ_BIT = 0x80
        self.MULTI_BIT = 0x40
        self.BW_RATE = 0x2c
        self.POWER_CTL = 0x2d
        self.DATAX0 = 0x32        # X-axis least significant byte

        # configuration parameters
        self.freq_max_spi = 100000
        self.v_freq = sample_rate
        self.spi_speed = 2000000           # SPI communication speed
        self.cold_start_samples = 2
        self.cold_start_delay = 0.1        # delay between cold start samples
        self.acc_conversion = 2 * 16.0/8192  # 2g range; 16-bit resolution; 8192 LSB/g

        self.pi = pigpio.pi()
        self.data = bytearray(b'\0\0\0\0\0\0\0') # buffer SPI data transmission

        # reading multiple data registers starting from DATAX0
        self.READ_DATA = self.data[:]
        self.READ_DATA[0] = self.DATAX0
        self.READ_DATA[0] |= self.MULTI_BIT
        self.READ_DATA[0] |= self.READ_BIT

        self.h = self.pi.spi_open(0, self.spi_speed, 3) # activate SPI on raspberry

        self.data[0] = self.BW_RATE
        self.data[1] = 0x0F # 0x0F sets output data rate to 3200Hz
        self.data[0] |= self.MULTI_BIT  # enable multi-byte write
        self.pi.spi_xfer(self.h, self.data[:2])

        self.data[0] = self.DATA_FORMAT
        self.data[1] = self.DATA_FORMAT_B
        self.data[0] |= self.MULTI_BIT
        self.pi.spi_xfer(self.h, self.data[:2])

        self.data[0] = self.POWER_CTL
        self.data[1] = 0x08 # measure mode set
        self.data[0] |= self.MULTI_BIT
        self.pi.spi_xfer(self.h, self.data[:2])

        self.cold_start() # cold start clear initial spurious readings
        self.delay = 1.0 / self.v_freq # delay between readings based on sample rate

    def cold_start(self):
        """ Performs initial readings to stabilize the sensor """
        for _ in range(self.cold_start_samples):
            count, data = self.pi.spi_xfer(self.h, self.READ_DATA)
            time.sleep(self.cold_start_delay)

    def moving_average_filter(self,signal,window_size):
        """ Implement a simple moving average filter to the input signal to smooth out data
        :param signal: input list of numerical data
        :param window_size: the size of the moving window for averaging
        :return: a list of moving averages
        """
        i = 0
        moving_averages = []
        arr = signal
        while i < len(arr) - window_size + 1:
            window = arr[i : i + window_size]
            window_average = round(sum(window) / window_size, 2)
            moving_averages.append(window_average)
            i += 1
        return moving_averages

    def read_one(self,acc_val):
        """ Read one set of accelerometer data, calculates the acceleration magnitude and identify potential fall events.
        :param acc_val:  list to store raw acceleration magnitude values for processing.
        :return: fall event detected.
        """
        state_fall = False
        TH_Free_Fall = 0.8  # threshold for free fall detection
        try:
            count, data = self.pi.spi_xfer(self.h, self.READ_DATA)
            if count == 7:
                # extract X, Y, Z acceleration values and apply conversion factor
                x = ct.c_int16(((data[2] << 8)) | data[1]).value * self.acc_conversion
                y = ct.c_int16(((data[4] << 8)) | data[3]).value * self.acc_conversion
                z = ct.c_int16(((data[6] << 8)) | data[5]).value * self.acc_conversion
                t = time.time() # timestamp of the reading

                acc = math.sqrt(x**2+y**2+z**2) # calculate acceleration magnitude
                acc_val.append(acc)

                if len(acc_val)>500:
                    mean = sum(acc_val) / len(acc_val)
                    acc_val = [item - mean for item in acc_val] # remove DC component
                    acc_val = self.moving_average_filter(acc_val,5) # apply moving average filter

                    minim = min(acc_val)
                    min_index = acc_val.index(minim)
                    maxim = max(acc_val)
                    max_index = acc_val.index(maxim)

                    # check for fall condition based on peak-to-trough difference
                    if (acc_val[max_index] - acc_val[min_index]) > TH_Free_Fall:
                        a = acc_val[max_index + 1:len(acc_val)]
                        new_fall = all((a[idx + 1] - a[idx]) < 0.5 for idx in range(len(a)-1))  # identify new movement
                        if new_fall:
                            state_fall = True # fall detected
                            acc_val = [] # clear buffer after detection
                        else:
                            state_fall = False

        except Exception as e:
            print('Err',e)
        return state_fall

    def close(self):
        """ Closes the SPI communication channel and releases resources"""
        self.pi.spi_close(self.h) # Commented out for Colab compatibility


# Example usage (commented out):
# adxl = ADXL345(sample_rate=100)
# acc_val = []
# while True:
#     state_fall = adxl.read_one(acc_val)
#     print('STATE :',state_fall)
#     time.sleep(0.02)
