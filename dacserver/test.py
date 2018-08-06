import threading
import time
def main():
    i = 1000000
    hello()
    while i > 0:
        print(i)
        i -= 1
        time.sleep(1)

def hello():
    timer = threading.Timer(2, hello)
    timer.start()
    print("helloooooooooooooo")

main()