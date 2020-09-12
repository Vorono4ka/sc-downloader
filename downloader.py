import os
import socket
import sys
from json import loads, load, dump

from requests import get

from utils.reader import Reader
from utils.writer import Writer


def exit():
    input('Press Enter to exit: ')
    sys.exit()


def mkdirs(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)


# Receiving all data
def recvall(sock: socket.socket, packet_length: int):
    received_data = b''
    while packet_length > 0:
        s = sock.recv(packet_length)
        if not s:
            raise EOFError
        received_data += s
        packet_length -= len(s)
    return received_data


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

    def brute_force(self):
        self.info['build'] = 0

        while downloader.code != 7:
            self.info['build'] += 1

            if self.info['build'] >= 300:
                self.info['build'] = 0
                self.info['major'] += 1

            self.send_client_hello()
            self.recv_data()

            if self.info['major'] >= config['major'] + 5:
                print('Version not matched!')
                exit()

    # Client Hello packet sending
    def send_client_hello(self):
        self.buffer = b''  # clear buffer

        self.writeUInt32(0)  # Protocol Version
        self.writeUInt32(11)  # Key Version
        self.writeUInt32(self.info['major'])  # major
        self.writeUInt32(self.info['revision'])  # revision
        self.writeUInt32(self.info['build'])  # build (minor)
        self.writeString('')  # ContentHash
        self.writeUInt32(2)  # DeviceType
        self.writeUInt32(2)  # AppStore

        packet_data = self.buffer
        self.buffer = b''
        self.writeUShort(10100)
        self.buffer += len(packet_data).to_bytes(3, 'big')
        self.writeUShort(0)
        self.buffer += packet_data

        self.s = socket.create_connection((self.info['server_ip'], 9339))

        self.s.send(self.buffer)

    # Login Failed packet receiving
    def recv_data(self):
        header = self.s.recv(7)
        packet_length = int.from_bytes(header[2:5], 'big')
        received_packet_data = recvall(self.s, packet_length)
        super().__init__(initial_bytes=received_packet_data)

        self.code = self.readUInt32()
        if self.code in [7, 8]:
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

    def download(self, path: str):
        if self.code == 7:
            request = get(f'{self.assets_url}/{self.finger["sha"]}/{path}')
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

    def __init__(self, initial_bytes: bytes = b'', info: dict = None):
        super().__init__(initial_bytes)
        self.s = None
        self.buffer = b''
        self.info = info

        self.content_url = None
        self.assets_url = None
        self.finger = None
        self.code = None


# Test
if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.mkdir('downloads')

    config = load(open('config.json'))

    downloader = Downloader(info={**config})

    downloader.send_client_hello()
    downloader.recv_data()

    if downloader.code != 7:
        print('Wrong version, version selection started!')
        downloader.brute_force()

    if downloader.code == 7:
        print('Version is founded!')
        dump(downloader.info, open('config.json', 'w'), indent=4)

    for file in downloader.finger['files']:
        file_path = file['file']

        if '/' in file_path:
            slash_index = file_path.index('/')
            folder = file_path[:slash_index]
            filename = file_path[slash_index + 1:]
        else:
            folder = ''
            filename = file_path

        mkdirs(f'downloads/{folder}')

        # Download all files
        # open(f'downloads/{folder}/{filename}', 'wb').write(downloader.download(file_path))

        # Download Specific File
        # open(f'file/path/filename.extension', 'wb').write(downloader.download('path/filename.extension'))
