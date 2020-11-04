import socket
from contextlib import contextmanager
import time
import atexit
import os
import select

address = "/tmp/test_address"

server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(address)
server.listen()

if __name__ == "__main__":
    atexit.register(os.remove, address)

    print("entering report loop")
    for i in range(100):

        readable, writable, errored = select.select([], server, [])

        for w in writable:
            sock, _ = server.accept()
        print(f"progress: {i}")
        time.sleep(0.01)
        server.sendall(str(i).encode())

    print("server exiting")


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