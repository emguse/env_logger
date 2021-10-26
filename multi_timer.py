import time

class multi_timer():
    def __init__(self, interval):
        self.last_time = 0.0
        self.up_state = False
        self.interval = interval
        
    def timer(self):
        if self.last_time + self.interval <= time.time():
            self.last_time = time.time()
            self.up_state = True

def main():
    INTERVAL_1s = float(1.0) # Enter the interval time in seconds
    INTERVAL_10s = float(10.0)  # Enter the interval time in seconds

    timer_1s = multi_timer(INTERVAL_1s)
    timer_10s = multi_timer(INTERVAL_10s)

    while True:
        timer_1s.timer()
        if timer_1s.up_state == True:
            timer_1s.up_state = False
            # Write the process here
            print("1sec: " + str(time.time()))
        timer_10s.timer()
        if timer_10s.up_state ==True:
            timer_10s.up_state = False
            # Write the process here
            print("10sec: " + str(time.time()))
    return

if __name__ == "__main__":
  main()