# Reliable UDP

Submitted by : 
<ul>
   <li> Thakur Shivank Singh - 2018A7PS0439H </li>
   <li> M. Nikhil Chandra    - 2018A7PS0260H </li>
   <li>R.V. Srinik          - 2018A7PS0266H</li>
   <li> Nitin Chandra        - 2018A7PS0188H</li>
   <li> Tejas Rajput         - 2018A7PS0253H</li>
</ul>
<br>
An application layer middleware protocol that implements reliable transfer of data over User Datagram Protocol. The protocol has been tested by transferring different types of files from the server to the client . Performance of the protocol was calculated with the data gathered from executing our protocol under different network conditions emulated by netem tool.
<br>
<br>

## Instructions for use
Open parallel terminals and run ServerApp.py and ClientApp.py simultaneously (Preferably, run ServerApp.py first). Provide the file name as a command-line argument to the server and the client program. The file to be sent from the server must be present in the "data/sender/" folder, and the file would be recevied on the client side in the "data/receiver/" folder.
After navigating to the folder on terminal, enter :

```
    python3 ServerApp.py <filename>

    python3 ClientApp.py <filename>
```

<br>

## Changes made to the original protocol


|                |Phase 1|Phase 2|
|----------------|-------------------------------|-----------------------------|
|1| Different packet structures were defined for different segments.         |Same packet structure was used for all segments.       |
|2|Connection  parameters like retransmission timeout, etc. are transferred through the SYN segment to the server.             |Connection parameters are taken to be known by both client and server before file transfer takes place.           |      |
|3| CHK control bit was used to indicate information about checksum.|CHK control bit was used to identify if the packet received contains data or not. |
|4| FIN control bit was used.           | The usage of FIN control bit was excluded in the implementation.       |
|5|Buffer size and window size for both receiver and sender were assumed to be the same.          |Window size is taken to be greater than buffer size.         |
|6| Data was supposed to be divided into 16 bit chunks.        |Data is divided into larger byte-sized chunks.



