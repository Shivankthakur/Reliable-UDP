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

from server import Sender
from server import SocketError
from server import FileNotExistError
from server import WindowSizeError


def ServerApp(filename):
    # Arguments
    # senderIP = "localhost"
    senderPort = 9000
    receiverPort = 8000
    sequenceNumberBits = 16
    windowSize = 1000
    timeout = 3

    # senderPort = int (input('Server Port number: '))
    # receiverPort = int (input('Client port number: '))
    # sequenceNumberBits = int (input("SequenceNumberBits : "))
    # windowSize = int (input("windowSize : "))
    # timeout = int (input("timeout : "))
    # fname = str(input('File Name: '))
    # if fname=="":
    #     fname = '200.gif'

    sender = Sender(senderPort=senderPort,
                    receiverPort=receiverPort,
                    sequenceNumberBits=sequenceNumberBits,
                    windowSize=windowSize,
                    timeout=timeout,
                    filename=filename
                    )

    try:
        # Create sending UDP socket
        sender.open()

        # # Send file to receiver
        print ('SEEEEEEEEEEEEEEEEEEEEND')

        # Close sending UDP socket
        sender.close()
        print ( 'Closeeeeeeed')

    except KeyboardInterrupt:
        print("ctrlc")
        sys.exit(0)
    except SocketError as e:
        print("Unexpected exception in sending UDP socket!!")
        print(e)
    except FileNotExistError as e:
        print("Unexpected exception in file to be sent!!")
        print(e)
    except WindowSizeError as e:
        print("Unexpected exception in window size!!")
        print(e)
    except Exception as e:
        print("Unexpected exception!")
        print(e)
    finally:
        sender.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage python3 ServerApp.py <filename>")
        sys.exit(0)

    filename = sys.argv[1]

    # Run Server Application
    ServerApp(filename)
