#!/usr/bin/python
'''
 Group members
    Thakur Shivank Singh - 2018A7PS0439H 
    M. Nikhil Chandra - 2018A7PS0260H 
    R.V. Srinik - 2018A7PS0266H 
    Nitin Chandra - 2018A7PS0188H 
    Tejas Rajput - 2018A7PS0253H
'''
 # Protocol Name => UDiPi

import os
import time
import math
import logging
import random
import socket
import struct
import select
import hashlib
import sys
from collections import namedtuple
from collections import OrderedDict
from threading import Thread
from threading import Lock
import pickle


# Set logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s SENDER [%(levelname)s] %(message)s',)
log = logging.getLogger()


# Lock for synchronized access to 'Window' class
LOCK = Lock()


class SocketError(Exception):
    pass


class FileNotExistError(Exception):
    pass


class WindowSizeError(Exception):
    pass


class Sender(object):
    """
    Sender running Selective Repeat protocol for reliable data transfer.
    """

    def __init__(self,
                 senderIP="localhost",
                 senderPort=10000,
                 receiverIP= '127.0.0.1',
                 receiverPort= 8080,
                 sequenceNumberBits=16,
                 windowSize=2,
                 maxSegmentSize=1500,
                 timeout=10,
                 filename="index.html",
                 www=os.path.join(os.getcwd(), "data", "sender")):
        self.senderIP = senderIP
        self.senderPort = senderPort
        self.sequenceNumberBits = sequenceNumberBits
        self.windowSize = windowSize
        self.maxSegmentSize = maxSegmentSize
        self.www = www
        self.receiverIP = receiverIP
        self.receiverPort = receiverPort
        self.timeout = timeout
        self.filename = filename

    def handshake(self):
        while 1:
            receivedSyn, _ = self.senderSocket.recvfrom(2048)
            packet = pickle.loads(receivedSyn)
            if packet["SYN"] == 1:
                log.info("received syn")
                break
        responseData = pickle.dumps("")
        responsePacket = PacketHandler.PACKET(SYN=1, ACK=1, SequenceNumber=0,
        Checksum=hashlib.md5(responseData).digest(), Data=responseData)
        window = Window(16, 1)
        window.consume(0)
        ackHandler = ACKHandler(self.senderSocket,
                                self.senderIP,
                                self.senderPort,
                                self.receiverIP,
                                self.receiverPort,
                                window,
                                timeout=self.timeout)
        ackHandler.start()
        singlePacket = SinglePacket(self.senderSocket,
                                            self.receiverIP,
                                            self.receiverPort,
                                            window,
                                            responsePacket,
                                            self.timeout,
                                            threadName="syn")

                # Start thread execution
        singlePacket.start()
        while (not window.empty()):
            log.info("waiting for ack")
            time.sleep(0.1)
        window.stop_transmission()
        # ackHandler.join()
        log.info("handshake completed")

    def open(self,bitError=.1):  #**********************************************EDITED
        """
        Create UDP socket for communication with the client.
        """
        log.info("Creating UDP socket %s:%d for communication with the client",
                  self.senderIP, self.senderPort)


        self.bitError= bitError

        while 1:
            self.senderSocket = socket.socket(socket.AF_INET,
                                            socket.SOCK_DGRAM)
            self.senderSocket.bind((self.senderIP, self.senderPort))

            self.handshake()
            self.send(self.filename, self.receiverIP, self.receiverPort, timeout=self.timeout)
            # fileName, address = self.senderSocket.recvfrom(4096)
            # if fileName :
            #     fileName = fileName.decode('utf-8')
            #     print (f'FILE REQUESTED: {fileName}')   #TIC
            #     receiverIP= '127.0.0.1'
            #     receiverPort=8080
            #     totalPackets="ALL"
            #     timeout=10
            #     self.send(fileName,
            #          receiverIP,
            #          receiverPort,
            #          totalPackets,
            #             timeout,self.bitError)


#*************************************************************************************************#

    def send(self,
             filename,
             receiverIP= '127.0.0.1',
             receiverPort= 8080,
             timeout=10):
        """
        Transmit specified file to the receiver.
        """
        log.info("Transmitting file '%s' to the receiver", filename)
        filename = os.path.join(self.www, filename)

        # If file does not exist, terminate the program
        if not os.path.exists(filename):
            raise FileNotExistError("File does not exist!\nFilename: %s"
                                    % filename)

        # Create an object of 'Window', which handles packet transmission
        window = Window(self.sequenceNumberBits,
                        self.windowSize, initval=1)


        # Create a thread named 'PacketHandler' to monitor packet transmission
        log.info("Creating a thread to monitor packet transmission")
        packetHandler = PacketHandler(filename,
                                      self.senderSocket,
                                      self.senderIP,
                                      self.senderPort,
                                      receiverIP,
                                      receiverPort,
                                      window,
                                      self.maxSegmentSize,
                                      timeout)

        # Create a thread named 'ACKHandler' to monitor acknowledgement receipt
        log.info("Creating a thread to monitor acknowledgement receipt")
        ackHandler = ACKHandler(self.senderSocket,
                                self.senderIP,
                                self.senderPort,
                                receiverIP,
                                receiverPort,
                                window,
                                timeout=self.timeout)

        # Start thread execution
        print('@'*50)
        log.info("Starting thread execution")
        print('@'*50)
        packetHandler.start()
        ackHandler.start()

        # Wait for threads to finish their execution
        packetHandler.join()
        ackHandler.join()
        log.info("File sent !")
        self.close()

    def close(self):
        """
        Close UDP socket.
        """
        try:
            if self.senderSocket:
                self.senderSocket.close()
                log.info("connection Close")
        except Exception as e:
            log.error("Could not close UDP socket!")
            log.debug(e)
            raise SocketError("Closing UDP socket %s:%d failed!"
                              % (self.senderIP, self.senderPort))


class Window(object):
    """
    Class for assisting packet transmission.
    """

    def __init__(self, sequenceNumberBits, windowSize=None, initval=0):
        self.expectedAck = initval
        self.nextSequenceNumber = initval
        self.nextPkt = 0        # maintains received packet count
        self.maxSequenceSpace = int(math.pow(2, sequenceNumberBits))
        if windowSize is None:
            self.maxWindowSize = int(math.pow(2, sequenceNumberBits-1))
        else:
            if windowSize > int(math.pow(2, sequenceNumberBits-1)):
                raise WindowSizeError("Invalid window size!!")
            else:
                self.maxWindowSize = windowSize
        self.transmissionWindow = OrderedDict()     # seq_num : [start_time, ack, nack]
        self.isPacketTransmission = True

    def expectedACK(self):
        return self.expectedAck

    def maxSequenceNumber(self):
        return self.maxSequenceSpace

    def empty(self):
        if 1:
            if len(self.transmissionWindow) == 0:
                return True
            return False

    def full(self):
        if 1:
            if len(self.transmissionWindow) >= self.maxWindowSize:
                return True
            return False

    def exist(self, key):
        if 1:
            if key in self.transmissionWindow:
                return True
            return False

    def next(self):
        return self.nextPkt

    def consume(self, key):
        with LOCK:
            self.transmissionWindow[key] = [None, False, False]

            self.nextSequenceNumber += 1
            if self.nextSequenceNumber >= self.maxSequenceSpace:
                self.nextSequenceNumber %= self.maxSequenceSpace

            self.nextPkt += 1

    def start(self, key):
        with LOCK:
            self.transmissionWindow[key][0] = time.time()

    def restart(self, key):
        with LOCK:
            self.transmissionWindow[key][0] = time.time()

    def stop(self, key):
        with LOCK:
            if self.exist(key):
                self.transmissionWindow[key][0] = None
            keys_to_delete = []
            # if we are expecting ACK for this packet...then process it....REORDERING
            if key == self.expectedAck:
                for k, v in self.transmissionWindow.items():
                    # packet seqnums to_delete from window that have been ACKed
                    if v[0] == None and v[1] == True:
                        keys_to_delete.append(k)
                    else:
                        break
                # print("keys_to_delete:", keys_to_delete)
                for k in keys_to_delete:
                    del self.transmissionWindow[k]

                if len(self.transmissionWindow) == 0:
                    self.expectedAck = self.nextSequenceNumber
                else:
                    self.expectedAck = list(self.transmissionWindow.items())[0][0]

    def start_time(self, key):
        return self.transmissionWindow[key][0]

    def unacked(self, key):
        with LOCK:
            # if packet seqnum exists in window and isACK is False
            if (self.exist(key) and self.transmissionWindow[key][1] == False):
                return True
            return False

    def mark_acked(self, key):
        with LOCK:
            self.transmissionWindow[key][1] = True

    def mark_nacked(self, key):
        with LOCK:
            self.transmissionWindow[key][2] = True

    def is_nacked(self, key):
        with LOCK:
            # if packet seqnum exists in window and isNACK is True
            if (self.exist(key) and self.transmissionWindow[key][2] == True):
                return True
            return False

    def stop_transmission(self):

             self.isPacketTransmission = False



    def transmit(self):
        return self.isPacketTransmission


class PacketHandler(Thread):
    """
    Thread for monitoring packet transmission.
    """

    #TIC PACKET HEADER
    HEADER_LENGTH = 6
    PACKET = namedtuple("Packet", ["SYN", "ACK", "SequenceNumber", "Checksum", "Data"])


    def __init__(self,
                 filename,
                 senderSocket,
                 senderIP,
                 senderPort,
                 receiverIP,
                 receiverPort,
                 window,
                 maxSegmentSize=1500,
                 timeout=10,
                 threadName="PacketHandler",
                 bufferSize=4096):
        Thread.__init__(self, daemon=True)
        self.filename = filename
        self.senderSocket = senderSocket
        self.senderIP = senderIP
        self.senderPort = senderPort
        self.receiverIP = receiverIP
        self.receiverPort = receiverPort
        self.window = window
        self.maxSegmentSize = maxSegmentSize
        self.maxPayloadSize = maxSegmentSize - PacketHandler.HEADER_LENGTH
        self.totalPackets = "ALL"
        self.timeout = timeout
        self.threadName = threadName
        self.bufferSize = bufferSize

    def run(self):
        """
        Start packet transmission.
        """
        # Get data from Application Layer and
        # create packets for reliable transmission
        log.info("[%s] Generating packets", self.threadName)
        packets = self.generate_packets()

        # Monitor sender
        # untill all packets are successfully transmitted and acked
        log.info("[%s] Starting packet transmission", self.threadName)
        while (not self.window.empty() or
                self.window.next() < self.totalPackets):
            # If window is full, then don't transmit a new packet
            if self.window.full():
                pass
            # If window is not full, but all packets are already transmitted;
            # then stop packet transmission
            elif (not self.window.full() and
                    self.window.next() >= self.totalPackets):
                pass
            # Transmit a new packet using underlying UDP protocol
            else:
                # Receive packet from Application Layer
                packet = packets[self.window.next()]

                # Slide transmission window by 1
                self.window.consume(packet.SequenceNumber)

                # Create a thread named 'SinglePacket'
                # to monitor transmission of single packet
                threadName = "Packet(" + str(packet.SequenceNumber) + ")"
                singlePacket = SinglePacket(self.senderSocket,
                                            self.receiverIP,
                                            self.receiverPort,
                                            self.window,
                                            packet,
                                            self.timeout,
                                            threadName=threadName)

                # Start thread execution
                singlePacket.start()

        # Stop packet transmission
        log.info("[%s] Stopping packet transmission", self.threadName)
        self.window.stop_transmission()
        #self.stop_transmission()

    def close(self):
        """
        Close UDP socket.
        """
        try:
            if self.senderSocket:
                self.senderSocket.close()
        except Exception as e:
            log.error("Could not close UDP socket!")
            log.debug(e)
            raise SocketError("Closing UDP socket %s:%d failed!"
                              % (self.senderIP, self.senderPort))

    def generate_packets(self):
        """
        Generate packets for transmitting to receiver.
        """
        packets = []

        with open(self.filename, "rb") as f:
            i = 1

            while True:
                # Read data such that
                # size of data chunk should not exceed maximum payload size
                data = f.read(self.maxPayloadSize)

                # If not data, finish reading
                if not data:
                    break

                # Set sequence number for a packet to be transmitted
                sequenceNumber = i % self.window.maxSequenceNumber()

                # Create a packet with required header fields and payload
                #TIC CREATING PACKET HEADER
                pkt = PacketHandler.PACKET(SequenceNumber=sequenceNumber,
                                           Checksum=self.checksum_new(data),
                                           Data=data, SYN=0, ACK=0)

                packets.append(pkt)

                i += 1

        # If total packets to be transmitted is not specified by user,
        # then transmit all available packets to receiver

        if self.totalPackets == "ALL":
            self.totalPackets = len(packets)
        else:
            if int(self.totalPackets) <= len(packets):
                self.totalPackets = int(self.totalPackets)
            else:
                self.totalPackets = len(packets)

        return packets[:self.totalPackets]

    def checksum_new(self, data):
        return hashlib.md5(data).digest()



class SinglePacket(Thread):
    """
    Thread for monitoring transmission of single packet.
    """

    def __init__(self,
                 senderSocket,
                 receiverIP,
                 receiverPort,
                 window,
                 packet,
                 timeout=10,
                 threadName="Packet(?)"):
        Thread.__init__(self, daemon=True)
        self.senderSocket = senderSocket
        self.receiverIP = receiverIP
        self.receiverPort = receiverPort
        self.window = window
        self.packet = packet
        self.timeout = timeout
        self.threadName = threadName

    def run(self):
        """
        Start monitoring transmission of single packet.
        """
        # Transmit a packet using underlying UDP protocol and
        # start the corresponding timer.
        log.info("[%s] Transmitting a packet with sequence number: %d",
                 self.threadName, self.packet.SequenceNumber)
        # print(self.window.transmissionWindow)
        self.rdt_send(self.packet)
        self.window.start(self.packet.SequenceNumber)

        # Monitor packet transmission, until it is acked
        while self.window.unacked(self.packet.SequenceNumber):
            timeLapsed = (time.time() -
                          self.window.start_time(self.packet.SequenceNumber))

            # Retransmit packet, if its transmission times out.
            # Also, restart the corresponding timer.
            # RESTRANSMISSION when packet unacked till timeout
            if (timeLapsed > self.timeout) or self.window.is_nacked(self.packet.SequenceNumber):
                log.info("[%s] Retransmitting a packet with sequence number: %d",
                         self.threadName, self.packet.SequenceNumber)
                self.rdt_send(self.packet)
                self.window.restart(self.packet.SequenceNumber)


        # Stop monitoring packet transmission, if it is successfully acked
        self.window.stop(self.packet.SequenceNumber)

    def rdt_send(self, packet):
        """
        Reliable data transfer.
        """

        # Create a raw packet
        rawPacket = self.make_pkt(packet)

        # Transmit a packet using UDP protocol
        self.udt_send(rawPacket)

    def make_pkt(self, packet):
        """
        Create a raw packet.
        """
        # sequenceNumber = struct.pack('=I', packet.SequenceNumber)
        # checksum = struct.pack('=H', packet.Checksum)
        # rawPacket = sequenceNumber + checksum + packet.Data.encode('utf-8') 
        packet_dict = {
            "SYN": packet.SYN,
            "ACK": packet.ACK,
            "FIN": 0,
            "CHK": 1,
            "KAL": 0,
            "NAK": 0,
            "ACKNUM": 0,
            "seqNum": packet.SequenceNumber,
            "checksum": packet.Checksum,
            "data": packet.Data,
        }
        return pickle.dumps(packet_dict)

    def udt_send(self, packet):
        """
        Unreliable data transfer using UDP protocol.
        """
        try:
            self.senderSocket.sendto(packet,
                                         (self.receiverIP, self.receiverPort))
        except Exception as e:
            log.error("[%s] Could not send UDP packet!", self.threadName)
            log.debug(e)
            raise SocketError("Sending UDP packet to %s:%d failed!"
                              % (self.receiverIP, self.receiverPort))


class ACKHandler(Thread):
    """
    Thread for monitoring acknowledgement receipt.
    """

    # ACK PACKET HEADER
    ACK = namedtuple("ACK", ["AckNumber", "Checksum", "Nack"])


    def __init__(self,
                 senderSocket,
                 senderIP,
                 senderPort,
                 receiverIP,
                 receiverPort,
                 window,
                 timeout=10,
                 ackLossProbability=0,
                 threadName="ACKHandler",
                 bufferSize=2048):
        Thread.__init__(self, daemon=True)
        self.senderSocket = senderSocket
        self.senderIP = senderIP
        self.senderPort = senderPort
        self.receiverIP = receiverIP
        self.receiverPort = receiverPort
        self.window = window
        self.timeout = timeout
        self.ackLossProbability = ackLossProbability
        self.threadName = threadName
        self.bufferSize = bufferSize

    def run(self):
        """
        Start monitoring acknowledgement receipt.
        """
        # Monitor sender
        # untill all packets are successfully transmitted and acked
        while self.window.transmit():
            # Wait(in while loop), if all the packets transmitted are acked and
            # if there are packets that are yet to be transmitted then go to next step
            if self.window.empty():
                continue

            # Listen for incoming acknowledgements on sender's socket
            # with the provided timeout
            ready = select.select([self.senderSocket], [], [], self.timeout)        # see select defn

            # if fd not ready
            if not ready[0]:
                continue

            # Receive acknowledgement
            try:
                receivedAck, receiverAddress = self.senderSocket.recvfrom(self.bufferSize)
            except Exception as e:
                log.error("[%s] Could not receive UDP packet!",
                          self.threadName)
                log.debug(e)
                raise SocketError("Receiving UDP packet failed!")

            # Verify whether the acknowledgement is received from correct receiver
            if receiverAddress[0] != self.receiverIP:
                continue

            # Parse header fields from the received acknowledgement
            receivedAck = self.parse(receivedAck)

            # Check whether the received acknowledgement is not corrupt
            # IGNORE/DISCARD corrupted ACK
            # if self.is_corrupt(receivedAck):
            #     log.warning("[%s] Received corrupt acknowledgement!!",
            #                 self.threadName)
            #     log.warning("[%s] Discarding acknowledgement with ack number: %d",
            #                 self.threadName, receivedAck.AckNumber)
            #     continue

            # If the received acknowledgement has acknowledgement number
            # beyond expected range, then discard the received acknowledgement
            # IF REPEATED ACK/OUT OF BOUND ACK...DISCARD
            if not self.window.exist(receivedAck.AckNumber):
                log.warning("[%s] Received acknowledgement outside transmission window!!",
                            self.threadName)
                log.warning("[%s] Discarding acknowledgement with ack number: %d",
                            self.threadName, receivedAck.AckNumber)
                continue

            # Mark transmitted packet as acked
            # for the corresponding received acknowledgement


            # The main function which marks ACK in transmissionWindow
            if receivedAck.Nack:
                log.info("[%s] Received negative acknowledgement with ack number: %d",
                     self.threadName, receivedAck.AckNumber)
                self.window.mark_nacked(receivedAck.AckNumber)
            else:
                log.info("[%s] Received acknowledgement with ack number: %d",
                     self.threadName, receivedAck.AckNumber)
                self.window.mark_acked(receivedAck.AckNumber)

    def parse(self, receivedAck):
        """
        Parse header fields from the received acknowledgement.
        """
        # ackNumber = struct.unpack('=I', receivedAck[0:4])[0]
        # checksum = struct.unpack('=16s', receivedAck[4:])[0]
        ackdict = pickle.loads(receivedAck)

        ack = ACKHandler.ACK(AckNumber=ackdict["ACKNUM"],
                             Checksum=ackdict["checksum"],
                             Nack=ackdict["NAK"])

        return ack

    def is_corrupt(self, receivedAck):
        """
        Check whether the received acknowledgement is corrupt or not.
        """
        # Compute hash code for the received acknowledgement
        hashcode = hashlib.md5()
        hashcode.update(str(receivedAck.AckNumber).encode('utf-8'))

        # Compare computed hash code
        # with the checksum of received acknowledgement
        if hashcode.digest() != receivedAck.Checksum:
            return True
        else:
            return False
