import grove_SHT35 as SHT35
import timekeeping
import db_sqlite
import csv
import datetime
import time
from collections import deque

READ_INTERVAL = 60 # [sec]
RECORD_LENGTH_H = 3600 # [sec](hour)
RECORD_LENGTH_D = 86400 # [sec](day)
SAVE_DIR_H = './log_h/'
SAVE_DIR_D = './log_d/'

class logger():
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
    def update(self):
        self.tk.update()
        if self.tk.just_second == True:
            self.read()
        if self.tk.just_minutes == True:
            self.export(self.d_data_h, 'hour')
        if self.tk.just_hour == True:
            self.export(self.d_data_d, 'day')
    def read(self):
        temperature, humidity = self.sht35.read()
        temperature = round(temperature, 2)
        humidity = round(humidity, 2)
        data = [temperature,humidity]
        print(data)
        tmp, hum = data
        self.db.insert_db(tmp, hum)
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

def main():
    log = logger()
    while True:
        log.update()

if __name__ == "__main__":
  main()