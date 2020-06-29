from json import loads

from utils.writer import Writer
from utils.reader import Reader
from requests import get
import socket


class Downloader(Reader, Writer):
    # Override string reading
    def readString(self):
        length = self.readUInt32()
        if length == 2**32 - 1:
            return ''
        else:
            return self.readChar(length)

    # Override string writing
    def writeString(self, string: str):
        encoded = string.encode('utf-8')
        self.writeUInt32(len(encoded))
        self.buffer += encoded

    # Receiving all data
    def recvall(self, sock: socket.socket, packet_length: int):
        received_data = b''
        while packet_length > 0:
            s = sock.recv(packet_length)
            if not s:
                raise EOFError
            received_data += s
            packet_length -= len(s)
        return received_data

    # Connecting to the Brawl Stars server
    def connect(self):
        self.s.connect(('game.brawlstarsgame.com', 9339))

    # Client Hello packet sending
    def send_client_hello(self, info: dict):
        self.writeUInt32(2)
        self.writeUInt32(11)
        self.writeUInt32(info['major'])
        self.writeUInt32(0)
        self.writeUInt32(info['minor'])
        self.writeUInt32(0)
        self.writeUInt32(2)
        self.writeUInt32(2)
        packet_data = self.buffer
        self.buffer = b''
        self.writeUShort(10100)
        self.buffer += len(packet_data).to_bytes(3, 'big')
        self.writeUShort(0)
        self.buffer += packet_data
        self.s.send(self.buffer)

    # Login Failed packet receiving
    def recv_data(self):
        header = self.s.recv(7)
        packet_length = int.from_bytes(header[2:5], 'big')
        received_packet_data = self.recvall(self.s, packet_length)
        super().__init__(initial_bytes=received_packet_data)
        self.code = self.readUInt32()
        self.finger = self.readString()
        self.readString()
        self.readString()
        self.readString()
        self.readString()
        self.readUInt32()
        self.readByte()
        self.readUInt32()
        self.readUInt32()
        self.content_url = self.readString()
        self.assets_url = self.readString()
        if self.code == 7:
            self.finger = loads(self.finger)

    def download(self, filename: str):
        if self.code == 7:
            request = get(f'{self.assets_url}/{self.finger["sha"]}/{filename}')
            status_code = request.status_code
            if status_code == 200:
                filedata = request.content

                return filedata
            else:
                print(f'Request error! Status code: {status_code}. '
                      f'Status: {"Page not found" if status_code == 404 else "unknown"}')
                return b'File not founded!'
        else:
            print(f'Error detected! Error code: {self.code}')
            return b''

    def __init__(self, initial_bytes: bytes = b''):
        super().__init__(initial_bytes)
        self.s = socket.socket()
        self.buffer = b''

        self.content_url = None
        self.assets_url = None
        self.finger = None
        self.code = None


# Test
if __name__ == '__main__':
    downloader = Downloader()
    downloader.connect()
    downloader.send_client_hello({'major': 27, 'minor': 267})
    downloader.recv_data()
    print(downloader.download('sc3d/8bit_geo.scw'))
# Test
