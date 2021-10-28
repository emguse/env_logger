import grove_SHT35 as SHT35
import timekeeping
import db_sqlite
import csv
import datetime
import time
from collections import deque
import RPi.GPIO as gpio
import pressure_DPS310 as DPS310
import acc_ADXL345 as ADXL345
import multi_timer
import paho.mqtt.publish as publish
import json

# press_acc event record constant
BUTTON_PIN = 5 # slot D5
SAVE_DIR = './press_log/'
RECORD_LENGTH = 20 # 1/2 past 1/2 future [sec]
BUTTON_MASK = 2.0 # [sec]
PRESS_READ_RATE = 64 # [Hz]
ACC_READ_RATE = 64 # [Hz]
REF_DELTA_P = 5 # [Pa]
REF_DELTA_ACC = 0.3 # [g]
# logging constant
READ_INTERVAL = 60 # [sec]
RECORD_LENGTH_H = 3600 # [sec](hour)
RECORD_LENGTH_D = 86400 # [sec](day)
SAVE_DIR_H = './log_h/'
SAVE_DIR_D = './log_d/'
# mqtt constant
BROKER = 'hanage'
PORT = 1883
TOPIC = "rspi/env"

class thp_logger():
    def __init__(self) -> None:
        self.sht35 = SHT35.GroveTemperatureHumiditySensorSHT3x()
        self.tk = timekeeping.timekeep()
        self.db = db_sqlite.db_entry()
        try:
            self.db.create_db()
        except:
            pass
        self.d_data_h = deque(maxlen=int(RECORD_LENGTH_H / READ_INTERVAL))
        self.d_data_d = deque(maxlen=int(RECORD_LENGTH_D / READ_INTERVAL))
        pass
    def update(self,press):
        self.tk.update()
        if self.tk.just_second == True:
            self.read(press)
        if self.tk.just_minutes == True:
            self.export(self.d_data_h, 'hour')
        if self.tk.just_hour == True:
            self.export(self.d_data_d, 'day')
    def read(self, press):
        temperature, humidity = self.sht35.read()
        temperature = round(temperature, 2)
        humidity = round(humidity, 2)
        press = round(press, 4)
        data = [temperature, humidity, press]
        print(data)
        msg = {'time':datetime.datetime.now(),'tmp':temperature, 'hum':humidity, 'atm':press}
        payload = json.dumps(msg)
        publish.single(TOPIC, payload, qos=0, hostname=BROKER, port=PORT)
        self.db.insert_db(temperature, humidity, press)
        self.d_data_h.append(data)
        self.d_data_d.append(data)
    def export(self, d, type):
        print("Start exporting")
        today = datetime.date.today()
        if type == 'hour':
            filename = str(SAVE_DIR_H + today.strftime('%Y%m%d') + '-' + time.strftime('%H%M%S') + '.csv')
        elif type == 'day':
            filename = str(SAVE_DIR_D + today.strftime('%Y%m%d') + '.csv')
        else:
            print('Unknown output period')
            return
        try:
            with open(filename, 'w', newline='') as f: # File open in write mode
                writer = csv.writer(f)
                for i in d:
                    writer.writerow(i)
                print('Export Complete')
        except:
            print('File export error')

class press_log():
    def __init__(self) -> None:
        self.dps310 = DPS310.pressure_sensor_DPS310() # Instance creation
        self.dps310_timer = multi_timer.multi_timer(self.dps310.read_interval) 
        self.Factors = self.dps310.read_calibration_coefficients() # Read Calibration Coefficients
        self.press = 0
        self.d_press = deque(maxlen=int(PRESS_READ_RATE * RECORD_LENGTH)) 
        self.last_p = 0
        pass
    def read_press(self):
        self.dps310_timer.timer() # Timer update
        if self.dps310_timer.up_state == True: # Time up judgment
            self.dps310_timer.up_state = False # Reset time-up status
            self.press = self.dps310.get_pressure(self.Factors) # DPS310 sensor reading
            press_data = [str(time.time()),str(self.press)] 
            self.d_press.append(press_data) # Add to queue
    def press_trigger_chk(self,b_up_state): 
        if self.last_p != 0: # Not detected the first time
            dp = abs(self.last_p - self.press) # Calculate the difference from the previous measurement
            if b_up_state == True: # Use the button's multiple detection prevention mask
                if dp >= REF_DELTA_P: # Determine if the difference exceeds the standard
                    b_up_state = False # Reset button mask status
                    self.press_trigger_after_record() # Record after triggering
            self.last_p = self.press # Update last measured value
        return b_up_state # Return the button mask status
    def press_trigger_after_record(self):
        print("Post-trigger pressure data recording")
        for i in range(int(PRESS_READ_RATE * RECORD_LENGTH /2)): # Counting half of the recording time
            while True: # Standby for timer-up
                self.dps310_timer.timer() # Timer update
                if self.dps310_timer.up_state == True: # Timer up to continue processing
                    break
            self.dps310_timer.up_state = False # Reset time-up status
            self.press = self.dps310.get_pressure(self.Factors) # DPS310 sensor reading
            press_data = [str(time.time()),str(self.press)]
            self.d_press.append(press_data) # Add to queue
        self.export_p(self.d_press,"dp") # Pressure data export
    def export_p(self, d_p, trg):
        today = datetime.date.today() # Get unix time.
        filename = str(SAVE_DIR + today.strftime('%Y%m%d') + '-' + time.strftime('%H%M%S') + trg +'_p.csv') # filename generation
        try:
            with open(filename, 'w', newline='') as f: # File open in write mode
                writer = csv.writer(f)
                print("Start exporting pressure data")
                for i in d_p:
                    writer.writerow(i) # Write the contents of the queue
                print("Export Complete")
        except:
            print("File export error")

class acc_log():
    def __init__(self) -> None:
        self.adxl345 = ADXL345.ADXL345() # Instance creation
        self.adxl345_timer = multi_timer.multi_timer(1/ACC_READ_RATE)
        self.d_acc = deque(maxlen=int(ACC_READ_RATE * RECORD_LENGTH))
        self.last_a = [0, 0, 0]
        self.ax = 0
        self.ay = 0
        self.az = 0
        pass
    def read_acc(self):
        self.adxl345_timer.timer() # Timer update
        if self.adxl345_timer.up_state == True: # Time up judgment
            self.adxl345_timer.up_state = False # Reset time-up status
            acc_data = self.adxl345.getAxes(True)
            acc_value = acc_data.values() # Convert a dictionary to a list of values only
            self.d_acc.append(acc_value) # Add to queue
            self.ax, self.ay, self.az = acc_value # Decompose the list
    def acc_trigger_chk(self, b_up_state):
        if b_up_state == True: # Make sure that the button is not masked with multiple protection.
            if self.last_a[0] != 0: # Not detected the first time
                dax = abs(self.last_a[0] - self.ax) # Calculate the difference from the previous measurement
                if dax >= REF_DELTA_ACC: # Determine if the difference exceeds the standard
                    b_up_state = False # Reset button mask status
                    self.acc_after_trigger_record('dax') # Start recording after trigger detection
            self.last_a[0] = self.ax # Update last measured value
            if self.last_a[1] != 0:
                day_ = abs(self.last_a[1] - self.ay)
                if day_ >= REF_DELTA_ACC:
                    b_up_state = False
                    self.acc_after_trigger_record('day')
            self.last_a[1] = self.ay
            if self.last_a[2] != 0:
                daz = abs(self.last_a[2] - self.az)
                if daz >= REF_DELTA_ACC:
                    b_up_state = False
                    self.acc_after_trigger_record('daz')
            self.last_a[2] = self.az
        return b_up_state
    def acc_after_trigger_record(self, trg):
        print("Post-trigger acceleration data recording")
        for i in range(int(PRESS_READ_RATE * RECORD_LENGTH /2)): # Counting half of the recording time
            while True: # Standby for timer-up
                self.adxl345_timer.timer() # Timer update
                if self.adxl345_timer.up_state == True: # Timer up to continue processing
                    break
            self.adxl345_timer.up_state = False # Reset time-up status
            acc_data = self.adxl345.getAxes(True) # ADXL345 sensor reading
            acc_value = acc_data.values() # Convert a dictionary to a list of values only
            self.d_acc.append(acc_value) # Add to queue
        self.export_a(self.d_acc, trg) # Export acceleration data
    def export_a(self, d_a, trg):
        today = datetime.date.today() # Get unix time.
        filename = str(SAVE_DIR + today.strftime('%Y%m%d') + '-' + time.strftime('%H%M%S') + trg + '_a.csv') # filename generation
        try:
            with open(filename, 'w', newline='') as f: # File open in write mode
                writer = csv.writer(f)
                print("Start exporting acc data")
                for i in d_a:
                    writer.writerow(i) # Write the contents of the queue
                print("Export Complete")
        except:
            print("File export error")

def main():
    gpio.setmode(gpio.BCM)
    gpio.setup(BUTTON_PIN,gpio.IN)
    button_mask = multi_timer.multi_timer(BUTTON_MASK)
    p_log = press_log()
    a_log = acc_log()
    log = thp_logger()
    try:
        p_log.dps310.start_measurement()
        while True:
            button_mask.timer()
            p_log.read_press()
            a_log.read_acc()
            log.update(p_log.press)
            button_mask.up_state = p_log.press_trigger_chk(button_mask.up_state)
            button_mask.up_state = a_log.acc_trigger_chk(button_mask.up_state)
            if gpio.input(BUTTON_PIN) and button_mask.up_state == True:
                button_mask.up_state = False
                print("Forced trigger detection")
                p_log.export_p(p_log.d_press, 'button')
                a_log.export_a(a_log.d_acc, 'button')              
    finally:
        p_log.dps310.stop_measurement()
        gpio.cleanup()


if __name__ == "__main__":
  main()