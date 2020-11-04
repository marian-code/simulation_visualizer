import socket
from contextlib import contextmanager
import time

address = "/tmp/test_address"

if __name__ == "__main__":

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(address)
        while True:
            time.sleep(0.01)
            data = s.recv(1024)
            if len(data) == 0:
                break
            else:
                print(data.decode("utf-8"))

        print("received zero length byte exiting")