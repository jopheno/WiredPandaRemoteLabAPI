import struct


class NetworkOutgoingMessage:
    def __init__(self, opcode):
        self._opcode = opcode

        self.byteArray = bytearray()
        self.byteArray.extend(opcode.to_bytes(length=1, byteorder='big'))
    
    def add_unsigned_byte(self, data):
        self.byteArray.extend(data.to_bytes(length=1, byteorder='big'))

    def add_unsigned_short(self, data):
        self.byteArray.extend(data.to_bytes(length=2, byteorder='big'))

    def add_unsigned_int(self, data):
        self.byteArray.extend(data.to_bytes(length=4, byteorder='big'))

    def add_unsigned_long(self, data):
        self.byteArray.extend(data.to_bytes(length=8, byteorder='big'))

    def add_header(self):
        auxByteArray = bytearray()

        value = 15
        auxByteArray.extend(value.to_bytes(length=1, byteorder='big'))

        value = 255
        for i in range(1, 9):
            auxByteArray.extend(value.to_bytes(length=1, byteorder='big'))

        value = 240
        auxByteArray.extend(value.to_bytes(length=1, byteorder='big'))

        self.byteArray[0:0] = auxByteArray

    def add_string(self, data):
        self.add_unsigned_short(len(data))
        self.byteArray.extend(data.encode('utf-8'))
    
    def add_size(self):
        self.byteArray[0:0] = len(self.byteArray).to_bytes(length=4, byteorder='big')
    
    def add_size_after_header(self):
        size_without_header = len(self.byteArray) - 10
        self.byteArray[10:10] = size_without_header.to_bytes(length=4, byteorder='big')
    
    def get_bytes(self):
      return self.byteArray
    
    def get_opcode(self):
        return self._opcode


class NetworkIncomingMessage:
    def __init__(self, opcode, buffer):
        self._opcode = opcode
        self._buffer = buffer
    
    def pop_unsigned_byte(self):
        data = struct.unpack("!B", bytearray(self._buffer[0:1]))[0]
        self._buffer = self._buffer[1:]
        return data
    
    def pop_unsigned_short(self):
        data = struct.unpack("!H", bytearray(self._buffer[0:2]))[0]
        self._buffer = self._buffer[2:]
        return data
    
    def pop_unsigned_int(self):
        data = struct.unpack("!I", bytearray(self._buffer[0:4]))[0]
        self._buffer = self._buffer[4:]
        return data
    
    def pop_unsigned_long(self):
        data = struct.unpack("!Q", bytearray(self._buffer[0:8]))[0]
        self._buffer = self._buffer[8:]
        return data
    
    def pop_float(self):
        data = struct.unpack("!f", bytearray(self._buffer[0:4]))[0]
        self._buffer = self._buffer[4:]
        return data
    
    def pop_double(self):
        data = struct.unpack("!d", bytearray(self._buffer[0:8]))[0]
        self._buffer = self._buffer[8:]
        return data
    
    def pop_string(self):
        size = self.pop_unsigned_short()
        ba = bytearray(self._buffer[0:size])
        self._buffer = self._buffer[size:]
        return ba.decode('utf-8')
    
    def get_size(self):
        return len(self._buffer)
    
    def get_opcode(self):
        return self._opcode
