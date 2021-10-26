import time

class timekeep():
    def __init__(self, s=0 , m=0 , h=0) -> None:
        self.just_second = False
        self.just_minutes = False
        self.just_hour = False
        self.std_s = s
        self.std_m = m
        self.std_h = h
        self.target = 0
        pass
    def set_mask(self):
        self.target = time.time() + 1
    def update(self):
        # seconds
        self.just_second = False
        if self.target <= time.time():
            if int(time.strftime('%S')) == self.std_s:
                self.set_mask()
                self.just_second = True
        # minutes
        self.just_minutes = False
        if int(time.strftime('%M')) == self.std_m:
            if self.just_second == True:
                self.just_minutes = True
        # hour
        self.just_hour = False
        if int(time.strftime('%H')) == self.std_h:
            if self.just_minutes == True:
                self.just_hour = True
def main():
    tk = timekeep()
    while True:
        tk.update()
        if tk.just_second == True:
            print('Just second: ' + time.strftime('%H%M%S'))
        if tk.just_minutes == True:
            print('Just minutes: ' + time.strftime('%H%M%S'))
        if tk.just_hour == True:
            print('Just hour: ' + time.strftime('%H%M%S'))

if __name__ == "__main__":
  main()