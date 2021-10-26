import time
from grove.i2c import Bus
import multi_timer
import csv
import datetime

READ_INTERVAL = 1/64 # [sec]
FILE_SAVE_INTERVAL = 3600 # [sec]
SAVE_DIR = 'press_log/'

# i2c address setting
ADDRESS = 0x77

# Pressure Configuration (PRS_CFG) 
PRESS_CONF = 0x63
    # Pressure measurement rate: 0110 XXXX- 64 measurements pr. sec.
    # Pressure oversampling rate: XXXX 0011 - 8 times.  Precision : 0.4 PaRMS.
    # 0111 0001 = 0x63 
'''DPS310 data sheet P.29 - 30
Pressure measurement rate: **)      |Pressure oversampling rate:
0000 - 1 measurements pr. sec.      |0000 - Single. (Low Precision)
0001 - 2 measurements pr. sec.      |0001 - 2 times (Low Power).
0010 - 4 measurements pr. sec.      |0010 - 4 times.
0011 - 8 measurements pr. sec.      |0011 - 8 times.
0100 - 16 measurements pr. sec.     |0100 *)- 16 times (Standard).
0101 - 32 measurements pr. sec.     |0101 *) - 32 times.
0110 - 64 measurements pr. sec.     |0110 *) - 64 times (High Precision).
0111 - 128 measurements pr. sec.    |0111 *) - 128 times.
Applicable for measurements         |1xxx - Reserved
in Background mode only             |*) Note: Use in combination with a bit shift.
**) note: There is a limit to the oversampling rate setting from 8 measurements pr. sec.
        (At 128 measurements per second, the oversampling rate is limited to 2)
'''

# Temperature Configuration(TMP_CFG) 
TEMP_CONF = 0xE0
    # Temperature measurement: 1XXX XXXX - External sensor (in pressure sensor MEMS element)
    # Temperature measurement rate: X110 XXXX - 64 measurements pr. sec.
    # Temperature oversampling (precision): 0000 - single. (Default) - Measurement time 3.6 ms.
    # 1110 0000 = 0xE0
'''DPS310 data sheet P.31
Temperature measurement                                 |
0 - Internal sensor (in ASIC)                           |
1 - External sensor (in pressure sensor MEMS element)   |
Temperature measurement rate:                           |Temperature oversampling (precision):
000 - 1 measurement pr. sec.                            |0000 - single. (Default) - Measurement time 3.6 ms.
001 - 2 measurements pr. sec.                           |
010 - 4 measurements pr. sec.                           |
011 - 8 measurements pr. sec.                           |
100 - 16 measurements pr. sec.                          |
101 - 32 measurements pr. sec.                          |
110 - 64 measurements pr. sec.                          |
111 - 128 measurements pr. sec.                         |
Applicable for measurements in Background mode only     |
'''

# Interrupt and FIFO configuration (CFG_REG)
INT_AND_FIFO_CONF = 0x00
    # T_SHIFT: bit3: Temperature result bit-shift: 0 - no shift result right in data register.
    # P_SHIFT: bit2: Pressure result bit-shift: 0 - no shift result right in data register.
    # not use interrupts.: 0000 XXXX
    # not use FIFO.      : XXXX XX0X
    # not use SPI.       : XXXX XXX0
    # 0000 1100 = 0x00
'''DPS310 data sheet P.33
If don't use interrupts. = 0000 XXXX 
T_SHIFT     | 3     | rw    | Temperature result bit-shift
                            | 0 - no shift.
                            | 1 - shift result right in data register.
                            | Note: Must be set to '1' when the oversampling rate is >8 times.
P_SHIFT     | 2     | rw    | Pressure result bit-shift
                            | 0 - no shift.
                            | 1 - shift result right in data register.
                            | Note: Must be set to '1' when the oversampling rate is >8 times.
If don't use FIFO.  = XXXX XX0X
If don't use SPI.   = XXXX XXX0
'''

# Sensor Operating Mode and Status (MEAS_CFG)
OP_MODE = 0x07
# 111 - Background Mode Continous pressure and temperature measurement
# 0000 0111 = 0x07
'''DPS310 data sheet P.32
Bits 7 to 4 are read-only and various ready statuses.
Bit 3 is reserved.
MEAS_CTRL   | 2:0   | rw    | Set measurement mode and type:
                            | Standby Mode
                            | 000 - Idle / Stop background measurement
                            | Command Mode
                            | 001 - Pressure measurement
                            | 010 - Temperature measurement
                            | 011 - na.
                            | 100 - na.
                            | Background Mode
                            | 101 - Continous pressure measurement
                            | 110 - Continous temperature measurement
                            | 111 - Continous pressure and temperature measurement
'''

# Compensation Scale Factors
SCALE_FACTOR_KP = 7864320 # Oversampling Rate 8 times
SCALE_FACTOR_TP = 524288 # Oversampling Rate 1 (single)
'''DPS310 data sheet P.15
Compensation Scale Factors
Oversampling Rate           | Scale Factor (kP or kT)   | Result shift ( bit 2and 3 address0x09)
-------------------------------------------------------------------------------------------------
1 (single)                  | 524288                    | 0
2 times (Low Power)         | 1572864                   | 0
4 times                     | 3670016                   | 0
8 times                     | 7864320                   | 0
16 times (Standard)         | 253952                    | enable pressure or temperature shift
32 times                    | 516096                    | enable pressure or temperature shift
64 times (High Precision)   | 1040384                   | enable pressure or temperature shift
128 times                   | 2088960                   | enable pressure or temperatureshift
'''

class pressure_sensor_DPS310():
    def __init__(self):
        time.sleep(0.1)
        self.read_interval = READ_INTERVAL
        self.adress = ADDRESS
        self.op_mode = OP_MODE
        # I2C bus
        self.bus = Bus(None)
        # Measurement Settings
        self.bus.write_byte_data(ADDRESS, 0x06, PRESS_CONF) 
        self.bus.write_byte_data(ADDRESS, 0x07, TEMP_CONF)
        self.bus.write_byte_data(ADDRESS, 0x09, INT_AND_FIFO_CONF)
        self.bus.write_byte_data(ADDRESS, 0x08, OP_MODE)

    def __getTwosComplement(self, raw, length):
       value = raw
       if raw & (1 << (length - 1)):
           value = raw - (1 << length)
       return value

    def read_calibration_coefficients(self):
        # Read Calibration Coefficients
        reg = {}
        for i in range(0x10, 0x22):
            reg[i] = self.bus.read_byte_data(ADDRESS,i)
        Factors = {}
        Factors['c0'] = self.__getTwosComplement(((reg[0x10]<<8 | reg[0x11])>>4), 12)
        Factors['c1'] = self.__getTwosComplement(((reg[0x11] & 0x0F)<<8 | reg[0x12]), 12)
        Factors['c00'] = self.__getTwosComplement((((reg[0x13]<<8 | reg[0x14])<<8 | reg[0x15])>>4), 20)
        Factors['c10'] = self.__getTwosComplement((((reg[0x15] & 0x0F)<<8 | reg[0x16])<<8 | reg[0x17]), 20)
        Factors['c01'] = self.__getTwosComplement((reg[0x18]<<8 | reg[0x19]), 16)
        Factors['c11'] = self.__getTwosComplement((reg[0x1A]<<8 | reg[0x1B]), 16)
        Factors['c20'] = self.__getTwosComplement((reg[0x1C]<<8 | reg[0x1D]), 16)
        Factors['c21'] = self.__getTwosComplement((reg[0x1E]<<8 | reg[0x1F]), 16)
        Factors['c30'] = self.__getTwosComplement((reg[0x20]<<8 | reg[0x21]), 16)
        return Factors

    def __calc_temp(self, raw_temp, Factors):
        scaled_temp = raw_temp / SCALE_FACTOR_TP # Traw_sc = Traw/kT
        compd_temp = Factors['c0'] * 0.5 + Factors['c1'] * scaled_temp # Tcomp (°C) = c0*0.5 + c1*Traw_sc
        return scaled_temp, compd_temp

    def read_temperature(self, Factors):
        reg = {}
        # read raw temperature
        for i in range(0x03, 0x06):
            reg[i] = self.bus.read_byte_data(ADDRESS,i)
        raw_temp = self.__getTwosComplement(((reg[0x03]<<16) | (reg[0x04]<<8) | reg[0x05]), 24)
        # calculate temperature
        scaled_temp, compd_temp = self.__calc_temp(raw_temp, Factors)
        return scaled_temp, compd_temp

    def __calc_press(self, raw_press, scaled_temp, Factors):
        # Praw_sc = Praw/kP
        scaled_press = raw_press / SCALE_FACTOR_KP
        # Pcomp(Pa) = c00 + Praw_sc*(c10 + Praw_sc *(c20+ Praw_sc *c30)) 
        #                + Traw_sc *c01 + Traw_sc *Praw_sc *(c11+Praw_sc*c21) 
        compd_press = Factors['c00'] + scaled_press * (Factors['c10'] + scaled_press\
                         * (Factors['c20'] + scaled_press * Factors['c30']))\
                            + scaled_temp * Factors['c01'] + scaled_temp * scaled_press\
                                 * (Factors['c11'] + scaled_press * Factors['c21'])
        return compd_press

    def read_pressure(self, scaled_temp, Factors):
        reg = {}
        for i in range(0x00, 0x03):
            reg[i] = self.bus.read_byte_data(ADDRESS,i)
        raw_press = self.__getTwosComplement(((reg[0x00]<<16) | (reg[0x01]<<8) | reg[0x02]), 24)
        compd_press = self.__calc_press(raw_press,scaled_temp, Factors)
        return compd_press
    
    def get_pressure(self, Factors):
        scaled_temp ,temperature = self.read_temperature(Factors) # read and compensation temperature
        press = self.read_pressure(scaled_temp, Factors) # read and compensation pressure
        return press

    def start_measurement(self):
        self.bus.write_byte_data(self.adress, 0x08, self.op_mode)
    def stop_measurement(self):
        self.bus.write_byte_data(self.adress, 0x08, 0x00)

def main():
    bus = Bus(None)
    INTERVAL = READ_INTERVAL
    timer = multi_timer.multi_timer(INTERVAL) 

    dps310 = pressure_sensor_DPS310() # Instance creation

    Factors = dps310.read_calibration_coefficients() # Read Calibration Coefficients

    while True:
        today = datetime.date.today()
        filename = str(SAVE_DIR + today.strftime('%Y%m%d') + '-' + time.strftime('%H%M%S') + '.csv')
        try:
            with open(filename, 'w', newline='') as f:
                dps310.start_measurement()
                bus.write_byte_data(ADDRESS, 0x08, OP_MODE)
                writer = csv.writer(f)
                file_start_time = time.time()
                while True:
                    timer.timer()
                    if timer.up_state == True:
                        timer.up_state = False

                        # process
                        scaled_temp ,temperature = dps310.read_temperature(Factors) # read and compensation temperature
                        press = dps310.read_pressure(scaled_temp, Factors) # read and compensation pressure
                        #print(str(time.time()) + "," + str(press))
                        data = [str(time.time()),str(press)]
                        writer.writerow(data)
                    if file_start_time+FILE_SAVE_INTERVAL <= time.time():
                        break
        finally:
            dps310.stop_measurement()

if __name__ == "__main__":
  main()