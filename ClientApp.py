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
import argparse
import sys
import time
import csv
from client import Receiver
from client import SocketError
from client import FileIOError
from client import WindowSizeError

def ClientApp(filename):
    # Arguments
    # senderIP =input('Server IP: ')
    senderPort = 9000
    receiverPort = 8000
    sequenceNumberBits = 16
    windowSize = 1000
    timeout = 3

    # senderPort = int (input('Server Port number: '))
    # receiverPort = int (input('Client port number: '))
    # sequenceNumberBits = int (input('sequenceNumberBits: '))
    # windowSize = int (input('Windows size: '))
    # timeout = int (input("timeout : "))
    # fname = str(input('File Name: '))
    # if fname=="":
    #     fname = '200.gif'


    # Create receiver UDP socket
    receiver = Receiver(receiverPort=receiverPort,
                        senderPort=senderPort,
                        sequenceNumberBits=sequenceNumberBits,
                        windowSize = windowSize)


    time_taken = receiver.receive(filename,
                    senderPort=senderPort,
                    timeout = timeout)

    # Close receiver UDP socket
    receiver.close()

    return time_taken


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage python3 ClientApp.py <filename>")
        sys.exit(0)

    filename = sys.argv[1]

    time_taken = ClientApp(filename)

    file_size = os.path.getsize('data/sender/'+filename)
    print(f"Sender file_size: {file_size}")
    throughput = file_size/time_taken
    print(f"Throughput: {throughput}")
    # print(f"{sys.argv[1]} {sys.argv[2]}%")
    # with open(sys.argv[1]+'.csv', 'a', newline='') as file:
    #     writer = csv.writer(file)
    #     writer.writerow([sys.argv[1], sys.argv[2], throughput, file_size, time_taken])
