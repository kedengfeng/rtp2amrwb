import argparse
from argparse import RawTextHelpFormatter

from bitstring import BitArray
import pyshark



__version__ = "0.2.4"
__author__ = "Nikolay Nenchev"

'''
Created by: Nikolay Nenchev
Date: 2015/07/27
Filename: rtp2amrwb.py

README:
python modules used:
bitstring-3.1.3.zip,
pyshark-0.3.3.zip (needs tshark binary)

Contribution
Original function amrPayload2Storage_EfficientMode taken from
http://pastebin.com/6fSKSJVv
'''

##################################################################
# convert amr payload to storage format
# according RFC 4867
# http://tools.ietf.org/html/rfc4867
# see http://packages.python.org/bitstring/walkthrough.html
#
# RFC 4867 (Bandwidth-Efficient Mode) p22...
# In the payload, no specific mode is requested (CMR=15), the speech
# frame is not damaged at the IP origin (Q=1), and the coding mode is
# AMR 7.4 kbps (FT=4).  The encoded speech bits, d(0) to d(147), are
# arranged in descending sensitivity order according to [2].  Finally,
# two padding bits (P) are added to the end as padding to make the
# payload octet aligned.
# 0                   1                   2                   3
# 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   | CMR=15|0| FT=4  |1|d(0)                                       |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                                                               |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                                                               |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                                                               |
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |                                                     d(147)|P|P|
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
#
# RFC 4867 Section 5.3 (AMR and AMR-WB Storage Format)
#   The following example shows an AMR frame in 5.9 kbps coding mode
#   (with 118 speech bits) in the storage format.
#    0                   1                   2                   3
#    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#   |P| FT=2  |Q|P|P|                                               |
#   +-+-+-+-+-+-+-+-+                                               +
#   |                                                               |
#   +          Speech bits for frame-block n, channel k             +
#   |                                                               |
#   +                                                           +-+-+
#   |                                                           |P|P|
#   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
#

def amrPayload2Storage_EfficientMode(payload):

    if (amr_type == 'nb'):
        # AMR-NR
        bitlen = [95, 103, 118, 134, 148, 159, 204, 244, 39]
        # print "selected codec is amr nb"
    elif (amr_type == 'wb'):
        # AMR-WB TS 26.201 - total bits
        bitlen = [132, 177, 253, 285, 317, 365, 397, 461, 477, 40]
        # print "selected codec is amr wb"
    else:
        exit(1)

    amr = BitArray(bytes=payload)
    cmr = amr[0:4]
    mode = amr[5:9]
    #print(mode.uint)
    #assert mode.uint >=0 and mode.uint <=8
    if not (mode.uint >= 0 and mode.uint <= 8):
        return
    else:
        qual = amr[9:10]
        voice = amr[10:10 + bitlen[mode.uint]]
        #print("cmr=%d\tmod=%d\tqual=%d\tvoicebits=%d" % (cmr.uint,mode.uint,qual.uint,voice.len))
        storage = BitArray(bin='0')
        storage.append(mode)
        storage.append(qual)
        storage.append('0b00')  # padding
        assert storage.len == 8, "check length of storage header is one byte"
        storage.append(voice)
        return storage.tobytes()



def writeBinaryAmrWB():
    with open(output_file, "w+b") as f:
        if (amr_type == 'nb'):
            f.write("#!AMR\n")
        elif (amr_type == 'wb'):
            f.write("#!AMR-WB\n")
        else:
            exit(1)
	f.close()

def appendBinaryAmrWB(nbytes):
    with open(output_file, "a+b") as f:
        f.write(nbytes)
    f.close()

def dump_rtp_payload():
    writeBinaryAmrWB()
    cap = pyshark.FileCapture(input_file, display_filter='amr or rtp')
    payload = ''
    for i in cap:
        try:
            #i.pretty_print()
            rtp = i[3] # without vlan layer in pcap
            # rtp = i[4] # with vlan layer in pcap
            # if i.rtp.payload:
            if rtp.payload:
                result = rtp.payload.replace(':', '').decode('hex')
                payload = payload + amrPayload2Storage_EfficientMode(result)
        except:
            # print("ne razpoznava rtp")
            pass
    return payload


def main():
    parser = argparse.ArgumentParser(description="Extract and save audio from PCAP RTP AMR NR or WB BE to media file",
		    formatter_class=RawTextHelpFormatter
		    )
    parser.add_argument('-i', dest="ifile", help='Input PCAP file containing RTP AMR-WB BE stream', required=True)
    parser.add_argument('-o', dest="ofile", help='Output file media file', required=True)
    parser.add_argument('-t', dest="type", choices=['nb', 'wb'], help='AMR NB(nb) or WB (wb)', required=True)
    args = parser.parse_args()

    global input_file 
    input_file = args.ifile
    global output_file 
    output_file = args.ofile
    global amr_type
    amr_type = args.type

    print 'Input file is:', input_file

    appendBinaryAmrWB(dump_rtp_payload())

    print 'Output file is:', output_file

if __name__ == "__main__":
    main()
