import time, os, datetime

while True:
    timeBegin = time.time()

    print(datetime.datetime.now())

    os.system(r"python C:\Users\giorgi2\Desktop\InstalDevChicker\InstallDevConfСhecker.py")

    timeEnd = time.time()
    timeElapsed = timeEnd - timeBegin
    time.sleep(1800 - timeElapsed)