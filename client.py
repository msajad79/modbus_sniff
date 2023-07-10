from pymodbus.client import ModbusSerialClient
import time

client = ModbusSerialClient(method='rtu', port='/dev/ttyUSB0', baudrate=9600)

client.connect()
while True:
    rr = client.read_input_registers(address=1, slave=1, count=2)
    try:
        print(rr.registers)
        time.sleep(1)
        #client.close()
    except:
        print("error")
        #time.sleep(1)
