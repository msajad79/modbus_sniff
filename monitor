import serial


def is_request(packet):
    """
    packet is bytes
    len packet is not 8 -> response
    packet[2] is not 3 -> request
    beacuse undifined register 300-399 (hex) else is -> request
    """
    if len(packet) != 8:
        return False
    elif packet[2] != 3:
        return True
    else:
        return True
    
def monitor_modbus():
    ser = serial.Serial(port, baudrate, timeout=3.0*11.0/baudrate)
    buffer = b""
    while True:
        ss = ser.read(1)
        if len(ss) != 0:
            buffer += ss
        elif len(buffer) != 0:
            packet_type = "Request " if is_request(buffer) else "Response"
            print(f"type = {packet_type}   slave id = {buffer[:1].hex()}     fcode = {buffer[1:2].hex()}     CRC = {buffer[-2:].hex(' ')}    data = {buffer[2:-2].hex('-')} ")
            #packets.append(buffer)
            buffer = b""

def monitor_hart():
    ser = serial.Serial(port, baudrate)
    buffer = b""
    while True:
        ss = ser.read(1)
        if len(ss) != 0:
            buffer += ss
        if buffer[-4:].hex() == "FFFF":
            print(buffer[:-4].hex())
            buffer = b""

if __name__ == "__main__":

    port = 'COM8'
    baudrate = 9600
    monitor_modbus()

