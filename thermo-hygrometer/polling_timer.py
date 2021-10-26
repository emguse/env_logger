import time

class polling_timer():
    def __init__(self, interval):
        t = time.time()
        f = 1 - (t - int(t))
        time.sleep(f)
        self.last_time = time.time()
        self.up_state = False
        self.interval = interval
        self.interval_colection = 0
        
    def timer(self):
        self.up_state = False
        if self.last_time + self.interval - self.interval_colection <= time.time():
            self.interval_colection = (time.time() - self.last_time) - self.interval
            self.last_time = time.time()
            self.up_state = True

def main():
    INTERVAL_1s = float(1.0) # Enter the interval time in seconds
    INTERVAL_10s = float(10.0)  # Enter the interval time in seconds

    timer_1s = polling_timer(INTERVAL_1s)
    timer_10s = polling_timer(INTERVAL_10s)

    while True:
        timer_1s.timer()
        if timer_1s.up_state == True:
            print("1sec: " + str(time.time()))
        timer_10s.timer()
        if timer_10s.up_state ==True:
            print("10sec: " + str(time.time()))
            
if __name__ == "__main__":
  main()