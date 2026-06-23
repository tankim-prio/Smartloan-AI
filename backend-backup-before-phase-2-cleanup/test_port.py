import socket

ports = [18000, 20000, 25000, 30000, 35000, 40000, 45000, 50000, 55000, 60000]

for port in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        s.close()
        print(f"WORKING_PORT={port}")
        break
    except OSError as e:
        print(f"BLOCKED {port}: {e}")
        s.close()
