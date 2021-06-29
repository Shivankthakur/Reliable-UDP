#!/usr/bin/python
'''
 Group members
    Thakur Shivank Singh - 2018A7PS0439H 
    M. Nikhil Chandra - 2018A7PS0260H 
    R.V. Srinik - 2018A7PS0266H 
    Nitin Chandra - 2018A7PS0188H 
    Tejas Rajput - 2018A7PS0253H
'''
import os
import time
import math
import logging
import socket
import struct
import select
import hashlib
from collections import namedtuple
from collections import OrderedDict
from threading import Thread
import pickle


# Set logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s RECEIVER [%(levelname)s] %(message)s',)
log = logging.getLogger()


class SocketError(Exception):
    pass


class FileIOError(Exception):
    pass


class WindowSizeError(Exception):
    pass


class Receiver(object):
    """
    Receiver running Selective Repeat protocol for reliable data transfer.
    """

    def __init__(self,
                 receiverIP="127.0.0.1",
                 receiverPort=8080,senderIP="localhost",
                 senderPort=10000,
                 sequenceNumberBits=16,
                 windowSize=2,
                 www=os.path.join(os.getcwd(), "data", "receiver")):
        self.receiverIP = receiverIP
        self.receiverPort = receiverPort
        self.sequenceNumberBits = sequenceNumberBits
        self.windowSize = windowSize
        self.www = www

    def open(self):
        """
        Create UDP socket for communication with the Server.
        """
        log.info("Creating UDP socket %s:%d for communication with the Server",
                 self.receiverIP, self.receiverPort)

    def receive(self,
                filename,
                senderIP="localhost",
                senderPort=10000,receiverIP="127.0.0.1",
                receiverPort=8080,
                timeout=10):

        self.SendeIP = senderIP
        self.senderPort = senderPort
        """
        Create UDP socket for communication with the Server.
        """
        log.info("Creating UDP socket %s:%d for communication with the Server",
                 self.receiverIP, self.receiverPort)
        self.receiverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiverSocket.bind((self.receiverIP, self.receiverPort))
        """
        Receive packets transmitted from sender and
        write payload data to the specified file.
        """
        log.info("Started to receive packets transmitted from sender")
        filenamePath = os.path.join(self.www, filename)
        start = time.time()
        # self.receiverSocket.sendto(filename.encode('utf-8'), (self.SendeIP,self.senderPort))
        # Create a file handler for writing data received from sender
        try:
            log.info("Writing payload data to '%s'", filenamePath)
            self.fileHandle = open(filenamePath, "wb")
        except IOError as e:
            log.error("Could not create a file handle!")
            log.debug(e)
            raise FileIOError("Creating a file handle failed!\nFilename: %s"
                              % filenamePath)

        # Create an object of 'Window', which handles packet receipt
        window = Window(self.sequenceNumberBits,
                        self.windowSize)

        # Create a thread named 'PacketHandler' to monitor packet receipt
        log.info("Creating a thread to monitor packet receipt")
        packetHandler = PacketHandler(self.fileHandle,
                                      self.receiverSocket,
                                      senderIP,
                                      senderPort,
                                      self.receiverIP,
                                      self.receiverPort,
                                      window,
                                      timeout)

        # Start thread execution
        print('@'*50)
        log.info("Starting thread execution")
        print('@'*50)
        packetHandler.start()

        # Wait for a thread to finish its execution
        packetHandler.join()
        time_taken = time.time() - start 
        print("Time taken:", time_taken)
        return time_taken


    def close(self):
        """
        Close a file handle and UDP socket.
        """
        # Close file handle
        try:
            if self.fileHandle:
                self.fileHandle.close()
        except IOError as e:
            log.error("Could not close a file handle!")
            log.debug(e)
            raise FileIOError("Closing a file handle failed!")

        # Close receiver's socket
        try:
            if self.receiverSocket:
                self.receiverSocket.close()
        except Exception as e:
            log.error("Could not close UDP socket!")
            log.debug(e)
            raise SocketError("Closing UDP socket %s:%d failed!"
                              % (self.receiverIP, self.receiverPort))


class Window(object):
    """
    Class for assisting packet receipt.
    """

    def __init__(self, sequenceNumberBits, windowSize=None):
        self.expectedPkt = 0            # received packet counter
        self.maxSequenceSpace = int(math.pow(2, sequenceNumberBits))
        if windowSize is None:
            self.maxWindowSize = int(math.pow(2, sequenceNumberBits-1))
        else:
            if windowSize > int(math.pow(2, sequenceNumberBits-1)):
                raise WindowSizeError("Invalid window size!!")
            else:
                self.maxWindowSize = windowSize
        self.lastPkt = self.maxWindowSize - 1
        self.receiptWindow = OrderedDict()      # similar to transmissionWindow functionality in server
        self.isPacketReceipt = False

    def expectedPacket(self):
        return self.expectedPkt

    def lastPacket(self):
        return self.lastPkt

    def out_of_order(self, key):
        if self.expectedPacket() > self.lastPacket():
            if key < self.expectedPacket() and key > self.lastPacket():
                return True
        else:
            if key < self.expectedPacket() or key > self.lastPacket():
                return True
        return False

    def exist(self, key):
        if key in self.receiptWindow and self.receiptWindow[key] != None:
            return True
        return False

    def store(self, receivedPacket):
        if not self.expected(receivedPacket.SequenceNumber):
            sequenceNumber = self.expectedPkt

            while sequenceNumber != receivedPacket.SequenceNumber:
                if sequenceNumber not in self.receiptWindow:
                    self.receiptWindow[sequenceNumber] = None

                sequenceNumber += 1
                if sequenceNumber >= self.maxSequenceSpace:
                    sequenceNumber %= self.maxSequenceSpace

        self.receiptWindow[receivedPacket.SequenceNumber] = receivedPacket

    def expected(self, sequenceNumber):
        if sequenceNumber == self.expectedPkt:
            return True
        return False

    def next(self):
        packet = None

        if len(self.receiptWindow) > 0:
            nextPkt = list(self.receiptWindow.items())[0]

            if nextPkt[1] != None:
                packet = nextPkt[1]

                del self.receiptWindow[nextPkt[0]]

                self.expectedPkt = nextPkt[0] + 1
                if self.expectedPkt >= self.maxSequenceSpace:
                    self.expectedPkt %= self.maxSequenceSpace

                self.lastPkt = self.expectedPkt + self.maxWindowSize - 1
                if self.lastPkt >= self.maxSequenceSpace:
                    self.lastPkt %= self.maxSequenceSpace

        return packet

    def receipt(self):
        return self.isPacketReceipt

    def start_receipt(self):
        self.isPacketReceipt = True


class PacketHandler(Thread):
    """
    Thread for monitoring packet receipt.
    """

    # PACKET and ACK STRUCTURE
    PACKET = namedtuple("Packet", ["SequenceNumber", "Checksum", "Data"])
    ACK = namedtuple("ACK", ["AckNumber", "Checksum", "Nack"])

    def __init__(self,
                 fileHandle,
                 receiverSocket,
                 senderIP,
                 senderPort,
                 receiverIP,
                 receiverPort,
                 window,
                 timeout=10,
                 bufferSize=4096):
        Thread.__init__(self)
        self.fileSize = 0
        self.fileHandle = fileHandle
        self.receiverSocket = receiverSocket
        self.senderIP = senderIP
        self.senderPort = senderPort
        self.receiverIP = receiverIP
        self.receiverPort = receiverPort
        self.window = window
        self.timeout = timeout
        self.bufferSize = bufferSize
        self.handshake_completed = False
        self.received_syn_ack = False

    def send_syn(self):
        data = pickle.dumps("")
        synDict = {
            "SYN": 1,
            "ACK": 0,
            "FIN": 0,
            "CHK": 0,
            "KAL": 0,
            "NAK": 0,
            "ACKNUM": 0,
            "checksum": hashlib.md5(data).digest(),
            "data": data,
            "seqNum": 0,
        }
        packet =  pickle.dumps(synDict)
        self.udt_send(packet)
        log.info("sent syn")

    def run(self):
        """
        Start monitoring packet receipt.
        """
        log.info("Started to monitor packet receipt")
        self.send_syn()
        # Monitor receiver
        # untill all packets are successfully received from sender
        chance = 0
        while True:
            # Listen for incoming packets on receiver's socket
            # with the provided timeout
            ready = select.select([self.receiverSocket], [], [], self.timeout)

            # If no packet is received within timeout;
            if not ready[0]:
                if not self.handshake_completed:
                    self.send_syn()
                    continue
                # Wait, if no packets are yet transmitted by sender
                if not self.window.receipt():
                    continue
                # Stop receiving packets from sender,
                # if there are more than 5 consecutive timeouts
                else:
                    if chance == 1:
                        #log.warning("Timeout!!")
                        #log.info("Gracefully terminating the receiver process, as Server stopped transmission!!")
                        log.info("File Received! Size: %d" % self.fileSize)
                        break
                    else:
                        chance += 1
                        continue
            else:
                chance = 0
                if not self.window.receipt():
                    self.window.start_receipt()

            # Receive packet
            try:
                receivedPacket, _ = self.receiverSocket.recvfrom(self.bufferSize)
            except Exception as e:
                log.error("Could not receive UDP packet!")
                log.debug(e)
                raise SocketError("Receiving UDP packet failed!")

            if not self.handshake_completed and not self.received_syn_ack:
                log.info("received a packet")
                synackPacket = pickle.loads(receivedPacket)
                print(synackPacket)
                if not (synackPacket["SYN"] == 1 and synackPacket["ACK"] == 1):
                    continue
                log.info("received syn ack")
                self.received_syn_ack = True
            # Parse header fields and payload data from the received packet
            receivedPacket = self.parse(receivedPacket)

            # Check whether the received packet is not corrupt
            
            if self.corrupt(receivedPacket):
                log.warning("Received corrupt packet!!")
                log.warning("Discarding packet with sequence number: %d",
                            receivedPacket.SequenceNumber)
                log.info("Transmitting a negative acknowledgement with ack number: %d",
                         receivedPacket.SequenceNumber)
                self.rdt_send(receivedPacket.SequenceNumber, nack=1)
                continue

            # If the received packet has out of order sequence number,
            # then discard the received packet and
            # send the corresponding acknowledgement
            if self.window.out_of_order(receivedPacket.SequenceNumber):
                log.warning("Received packet outside receipt window!!")
                log.warning("Discarding packet with sequence number: %d",
                            receivedPacket.SequenceNumber)

                # Reliable acknowledgement transfer
                log.info("Transmitting an acknowledgement with ack number: %d",
                         receivedPacket.SequenceNumber)
                self.rdt_send(receivedPacket.SequenceNumber)

                continue

            # If received packet is duplicate, then discard it
            # DUPLICATION - if dup pkt then ignore else store pkt
            if self.window.exist(receivedPacket.SequenceNumber):
                log.warning("Received duplicate packet!!")
                log.warning("Discarding packet with sequence number: %d",
                            receivedPacket.SequenceNumber)
                continue
            # Otherwise, store received packet into receipt window and
            # send corresponding acknowledgement
            else:
                log.info("Received packet with sequence number: %d",
                         receivedPacket.SequenceNumber)

                self.window.store(receivedPacket)

                log.info("Transmitting an acknowledgement with ack number: %d",
                         receivedPacket.SequenceNumber)
                self.rdt_send(receivedPacket.SequenceNumber)        #seq num is passed...but is actually ack num for the client that needs to send ACK now

            # If sequence number of received packet matches with the expected packet,
            # then deliver the packet and all consecutive previously arrived &
            # stored packets to Application Layer

            # REORDERING...checks if expectedPkt is received pkt seqnum. If not then goes back in the while true loop
            if self.window.expected(receivedPacket.SequenceNumber):
                if receivedPacket.SequenceNumber == 1:
                    self.handshake_completed = True
                self.deliver_packets()

    def parse(self, receivedPacket):
        """
        Parse header fields and payload data from the received packet.
        """
        packet = pickle.loads(receivedPacket)
        # header = receivedPacket[0:6]    #first 6 elements of received packet...=>header
        # data = receivedPacket[6:]

        # sequenceNumber = struct.unpack('=I', header[0:4])[0]
        # checksum = struct.unpack('=H', header[4:])[0]

        packet = PacketHandler.PACKET(SequenceNumber=packet["seqNum"],
                                      Checksum=packet["checksum"],
                                      Data=packet["data"])

        return packet

    def corrupt(self, receivedPacket):
        """
        Check whether the received packet is corrupt or not.
        """
        # Compute checksum for the received packet
        computedChecksum = self.checksum_new(receivedPacket.Data)

        # Compare computed checksum with the checksum of received packet
        if computedChecksum != receivedPacket.Checksum:
            return True
        else:
            return False

    def checksum_new(self, data):
        return hashlib.md5(data).digest()

    def rdt_send(self, ackNumber, nack=0):
        """
        Reliable acknowledgement transfer.
        """
        ack = PacketHandler.ACK(AckNumber=ackNumber,
                                Checksum=self.get_ack_checksum(),
                                Nack=nack)

        # Create a raw acknowledgement
        rawAck = self.make_pkt(ack)

        # Transmit an acknowledgement using underlying UDP protocol
        self.udt_send(rawAck)

    def get_ack_checksum(self):
        return hashlib.md5(pickle.dumps("")).digest()

    def get_hashcode(self, data):
        """
        Compute the hash code.
        """
        hashcode = hashlib.md5(data)
        return hashcode.digest()

    def make_pkt(self, ack):
        """
        Create a raw acknowledgement.
        """
        ackNumber = struct.pack('=I', ack.AckNumber)
        checksum = struct.pack('=16s', ack.Checksum)
        rawAck = ackNumber + checksum
        ackdict = {
            "SYN": 0,
            "ACK": 1 if ack.Nack == 0 else 0,
            "FIN": 0,
            "CHK": 0,
            "KAL": 0,
            "NAK": ack.Nack,
            "ACKNUM": ack.AckNumber,
            "checksum": ack.Checksum,
            "data": "",
            "seqNum": 0,
        }
        return pickle.dumps(ackdict)

    def udt_send(self, ack):
        """
        Transmit an acknowledgement using underlying UDP protocol.
        """
        try:
            self.receiverSocket.sendto(ack, (self.senderIP, self.senderPort))
        except Exception as e:
            log.error("Could not send UDP packet!")
            log.debug(e)
            raise SocketError("Sending UDP packet to %s:%d failed!"
                              % (self.senderIP, self.senderPort))

    def deliver_packets(self):
        """
        Deliver packets to Application Layer.
        """
        while True:
            # Get the next packet to be delivered to Application Layer
            packet = self.window.next()

            # If next packet is available for delivery,
            # then deliver data to Application Layer
            if packet and packet.SequenceNumber != 0:
                log.info("Delivered packet with sequence number: %d",
                         packet.SequenceNumber)
                self.deliver(packet.Data)
            else:
                break

    def deliver(self, data):
        """
        Deliver data to Application Layer.
        """
        try:
            self.fileSize += len(data)
            self.fileHandle.write(data)
        except IOError as e:
            log.error("Could not write to file handle!")
            log.debug(e)
            raise FileIOError("Writing to file handle failed!")
