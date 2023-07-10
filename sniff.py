import struct
from abc import ABC
import serial
import threading
import queue

def computeCRC(data):  # pylint: disable=invalid-name
    """Compute a crc16 on the passed in string.

    For modbus, this is only used on the binary serial protocols (in this
    case RTU).

    The difference between modbus's crc16 and a normal crc16
    is that modbus starts the crc value out at 0xffff.

    :param data: The data to create a crc16 of
    :returns: The calculated CRC
    """
    crc = 0xFFFF
    for data_byte in data:
        idx = __crc16_table[(crc ^ int(data_byte)) & 0xFF]
        crc = ((crc >> 8) & 0xFF) ^ idx
    swapped = ((crc << 8) & 0xFF00) | ((crc >> 8) & 0x00FF)
    return swapped


class ABSPacket(ABC):
    def __init__(self) -> None:
        pass

class RequestPacket(ABSPacket):
    def __init__(self, slave_id, fcode, start_register, quantity, CRC=None) -> None:
        super().__init__()
        self.slave_id = slave_id
        self.fcode = fcode
        self.start_register = start_register
        self.quantity = quantity
        self.CRC = CRC

    def calculate_expected_response_length(self):
        BASE_ADU_SIZE = 3
        expected_response_length = 1 + 1 + 2 * self.quantity + BASE_ADU_SIZE
        return expected_response_length

class ResponsePacket(ABSPacket):
    def __init__(self, req, slave_id, fcode, data, CRC) -> None:
        self.req:RequestPacket = req
        super().__init__()
        self.slave_id = slave_id
        self.fcode = fcode
        self.data = data
        self.CRC = CRC
        self.registers = []
        
    def decode_registers(self, register_size, mode):
        self.registers = []
        for i in range(self.req.quantity):
            self.registers.append(struct.unpack(mode, self.data[register_size*i:register_size*(i+1)])[0])

    def decode(self):
        register_size = int(len(self.data) / self.req.quantity)
        if register_size == 2:
            return self.decode_registers(register_size, ">h")
        elif register_size == 4:
            return self.decode_registers(register_size, ">f")
        elif register_size == 8:
            return self.decode_registers(register_size, ">d")
        raise Exception(f"register size is {register_size} please check decode response and select type for this data {self.data}")
    
class ModbusRTUSniff():

    def __init__(self, port, baudrate, target_register) -> None:
        self.target_register = target_register
        self.baudrate = baudrate
        self.port = port
        self.client = self.connect()
        self.state = 0
        self.pending_request:RequestPacket = None
        
        self.q = queue.Queue()

        self.packets = []
        self.thread_read_packet = threading.Thread(target=self.get_packet)
        self.thread_read_packet.start()
        
    def connect(self):
        """
        connect to modbus serial RTU 
        """
        #client = ModbusSerialClient(method='rtu', port=self.port, baudrate=self.baudrate)
        #client.connect()
        client = serial.Serial(self.port, self.baudrate, timeout=3.5*11.0/self.baudrate)
        return client

    def get_packet(self):
        buffer = b""
        while True:
            result = self.client.read(1)
            if len(result) != 0:
                buffer += result
            elif len(buffer) != 0:
                self.q.put(buffer)
                buffer = b""

    def detect_pattern_serial(self, request_pattern:RequestPacket):
        """
        detect pattern on serial
        """
        while True:
            for packet_pattern_b in request_pattern.build_packet():
                packet_b = self.client.recv(1)
                if packet_b.hex() != '{:02x}'.format(packet_pattern_b):
                    break
            else:
                self.state = 2
                self.pending_request = request_pattern
                print("**** OK ****")
                return "OK"

    def is_request(self, packet):
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

    def check_CRC(self, data):
        return True if struct.pack(">H", computeCRC(data[:-2])) == data[-2:] else False

    def add_request_pending(self, packet):
        slave_id = packet[0]
        fcode = packet[1]
        if fcode > 0x80:
            print(f"Packet, detected REQUEST but fcode is {fcode} !")
            return
        start_register = struct.unpack(">H", packet[2:4])[0]
        quantity = struct.unpack(">H", packet[4:6])[0]
        self.pending_request = RequestPacket(
            slave_id=slave_id, 
            fcode=fcode, 
            start_register=start_register, 
            quantity=quantity,
            CRC=packet[-2:]
        )
        return

    def recv_res(self, packet):
        slave_id = packet[0]
        fcode = packet[1]
        if fcode > 0x80:
            print(f"Packet exception {fcode} !")
            self.pending_request = None
            return
        bytes_count = struct.unpack(">B", packet[2:3])[0]
        res = ResponsePacket(
            req=self.pending_request,
            slave_id=slave_id,
            fcode=fcode,
            data=packet[3:-2],
            CRC=packet[-2:]
        )
        return res

    def save_data(self, res:ResponsePacket):
        data = res.registers[self.target_register - res.req.start_register]
        print(data)

    def sniffing(self):
        while True:
            packet = self.q.get()
            if not self.check_CRC(packet):
                continue
            
            if self.is_request(packet):
                self.add_request_pending(packet)
            else:
                if self.pending_request is None:
                    continue
                res:ResponsePacket = self.recv_res(packet)
                if res is None:
                    continue
                res.decode()
                
                if res.req.start_register <= self.target_register  and self.target_register < res.req.start_register+res.req.quantity:
                    self.save_data(res)
                self.pending_request = None

if __name__ == "__main__":
    sniff = ModbusRTUSniff("COM8", 9600, 2)
    sniff.sniffing()
    
