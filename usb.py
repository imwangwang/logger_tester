import sys
from threading import Thread, Lock
import serial
import binascii
import struct
from Queue import Queue

channelNum = 32
mutex = Lock()
# 32 channels of 128KB in each channel
chan_buf = [[0 for j in range(128 * 1024)] for i in range(channelNum)]
chan_walk = 0
chan_left = (0, False)

def receive(lser, nut):
    global q
    global chan_buf
    global chan_walk
    while True:
        item = q.get()
        if item == "stop":
            continue
        elif item == "poll32":
            mutex.acquire()
            dat = lser.read(40960)
            if len(dat) != 0:
                print("Read %d Bytes from USB"%len(dat))
            else:
                continue

            if chan_left[1]:
                dat.insert(0, chan_left[0])
                chan_left = (0, False)

            m = 0
            n = m + 2
            while n <= len(dat):
                chan_buf[chan_walk].append(struct.unpack('<H', bytearray(dat[m:n])))
                chan_buf[chan_walk].pop(0)
                m = n
                n = m + 2
                chan_walk = chan_walk + 1
                chan_walk = chan_walk % channelNum

            if n > len(dat) :
                chan_left = (dat[-1], True)

            mutex.release()
            q.put("poll32")
        elif item == "poll1-16":
            mutex.acquire()
            dat = lser.read(40960)
            if len(dat) != 0:
                print("Read %d Bytes from USB"%len(dat))
            mutex.release()
            q.put("poll1-16")
        elif item == "poll16-32":
            mutex.acquire()
            dat = lser.read(40960)
            if len(dat) != 0:
                print("Read %d Bytes from USB"%len(dat))
            mutex.release()
            q.put("poll16-32")
        elif item == "quit":
            break

hello = bytearray([0xA5, 0x04, 0x00, 0x00])
expected_ack = bytearray([0x5A, 0xFE, 0x00, 0x00])

q = Queue()
path = sys.argv[1]
ser = serial.Serial(path, 115200, timeout = 1, rtscts=0)
print(ser.name)
ser.write(hello)
s = ser.read(4)
rcv = None
print binascii.hexlify(s)
if s == expected_ack:
    print("Got ACK")
    rcv = Thread(target=receive, args=(ser, None))
    rcv.start()
    while True:
        cmd = raw_input("input command to continue...")
        if cmd == 'r1':
            mutex.acquire()
            sample1 = bytearray([0xA5, 0x01, 0xE8, 0x03])
            ser.write(sample1)
            s = ser.read(4)
            if s == expected_ack:
                q.put("poll1-16")
            mutex.release()
        elif cmd == 'r2':
            mutex.acquire()
            sample2 = bytearray([0xA5, 0x02, 0x30, 0x75])
            ser.write(sample2)
            s = ser.read(4)
            if s == expected_ack:
                q.put("poll16-32")
            mutex.release()
        elif cmd == 'rall':
            mutex.acquire()
#            sample2 = bytearray([0xA5, 0x06, 0xD0, 0x07])
            sample2 = bytearray([0xA5, 0x06, 0xE8, 0x03])
#            sample2 = bytearray([0xA5, 0x06, 0xB8, 0x0B])
            ser.write(sample2)
            s = ser.read(4)
            if s == expected_ack:
                q.put("poll32")
            mutex.release()
        elif cmd == 's':
            mutex.acquire()
            stop = bytearray([0xA5, 0x03, 0x00, 0x00])
            ser.write(stop)
            q.put("stop")
            mutex.release()
        elif cmd == 'q':
            mutex.acquire()
            stop = bytearray([0xA5, 0x03, 0x00, 0x00])
            ser.write(stop)
            q.put("quit")
            mutex.release()
            break
    rcv.join()
else:
    print("No response")

print("Quit...")



