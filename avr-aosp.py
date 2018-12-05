#!/usr/bin/python

"""
 *
 * Copyright (c) 2018
 *   Balint Cristian <cristian dot balint at gmail dot com>
 *
 * AVR AOSP like programmer (see AVR911)
 *
"""

"""

  avr-aosp.py (Implement basic AVR911 bootloader communication as "AVR opensource programmer" )

"""


import sys
import time
import binascii

import serial


nLastTick=-1
def TermProgress( dfComplete, pszMessage, pProgressArg ):

  global nLastTick
  nThisTick = (int) (dfComplete * 40.0)

  if nThisTick < 0:
    nThisTick = 0
  if nThisTick > 40:
    nThisTick = 40

  # Have we started a new progress run?
  if nThisTick < nLastTick and nLastTick >= 39:
    nLastTick = -1

  if nThisTick <= nLastTick:
    return True

  while nThisTick > nLastTick:
    nLastTick = nLastTick + 1
    if (nLastTick % 4) == 0:
      sys.stdout.write('%d' % ((nLastTick / 4) * 10))
    else:
      sys.stdout.write('.')

  if nThisTick == 40:
    print(" - done." )
  else:
    sys.stdout.flush()

  return True

def GetParams( fd ):

  print
  print "INFO"
  print

  fd.write("S")
  fd.flush()
  print "  S =", fd.read(7), "\t#programmer id"

  fd.write("V")
  fd.flush()
  print "  V =", fd.read(2), "\t#software version"

  fd.write("v")
  fd.flush()
  print "  v =", fd.read(1), "\t#hardware version"

  fd.write("p")
  fd.flush()
  print "  p =", fd.read(1), "\t#programmer type"

  fd.write("a")
  fd.flush()
  print "  a =", fd.read(1), "\t#autoincrement support"

  fd.write("b")
  fd.flush()
  print "  b =", fd.read(1), "\t#block mode support"

  fd.write("t")
  fd.flush()
  print "  t = [%s]" % str(binascii.hexlify(fd.read(2))), "\t#supported device code"

  fd.write("s")
  fd.flush()
  print "  s =", str(binascii.hexlify(fd.read(3))), "\t#signature"

  fd.write("N")
  fd.flush()
  print "  N =", fd.read(1), "\t#high fuse bits"

  fd.write("F")
  fd.flush()
  print "  F =", fd.read(1), "\t#low fuse bits"

  fd.write("r")
  fd.flush()
  print "  r =", fd.read(1), "\t#lock bits"

  fd.write("Q")
  fd.flush()
  print "  Q =", fd.read(1), "\t#extended fuse bits"


def SetAddr( fd, addr):

    hexadr = "%04x" % addr
    addrhi = hexadr[0:2]
    addrlo = hexadr[2:4]

    if ( addr < 0x10000 ):
      fd.write("A%c%c" % (addrhi.decode('hex'), addrlo.decode('hex')))
    else:
      fd.write("H%c%c" % (addrhi.decode('hex'), addrlo.decode('hex')))
    fd.flush()
    if (fd.read(1) != '\r'):
      print "ERROR: Address not acknowleged."
      sys.exit(-1)


def ReadPGMMem( fd, filename, morg, mend ):

  mem = []

  print
  print "READ program memory [0x%04X - 0x%04X] @%s #%i bytes" % (morg,mend,filename,(mend-morg)*2)

  for addr in range(morg, mend):

    SetAddr( fd, addr )

    fd.write("R")
    fd.flush()
    data = fd.read(2)

    mem.append(data)

    TermProgress( float( addr ) / float( mend-morg ), None, None )

  TermProgress( 1.0, None, None )

  fl = open(filename, 'w')

  chk = 0
  for i in range(morg, mend):

    addr = morg + i
    indx = addr - morg

    memlo = ord( mem[indx][1] )
    memhi = ord( mem[indx][0] )

    if ( addr % 0x8 == 0 ):

      slen = ((mend - i) * 2)
      if ( slen >= 0x10 ):
        slen = 0x10

      if ( indx > 0 ):
        fl.write( "%02X\r\n:%02X%04X00" % (-(chk)&0xFF, slen, addr*2) )
      else:
        fl.write( ":%02X%04X00" % (slen, addr*2) )

      chk = slen + ((addr*2) >> 8) + ((addr*2) & 0x00FF)

    chk = chk + memlo + memhi

    fl.write( "%02X%02X" % ( memlo, memhi ) )

  fl.write( "%02X\r\n" % ( -(chk)&0xFF  ) )
  fl.write( ":00000001FF\r\n" )
  fl.flush()

  print

  fl.close()


def EraseFlash( fd ):

  print
  print "ERASE program memory"
  print

  fd.write("e")
  fd.flush()
  if (fd.read(1) != '\r'):
    print "ERROR: Flash erase not acknowleged."
    sys.exit(-1)


def BurnHexFile( fd, filename ):

  alen = 0
  fl = open(filename, 'r')
  for l in fl.read().split('\n'):
    if ( ':' in l ):
      alen = alen + int(l[1:3], 16)
  fl.close()

  print
  print "WRITE program memory [%s] #%i bytes" % (filename, alen)

  fl = open(filename, 'r')

  for l in fl.read().split('\n'):
    if ( ':' in l ):

      slen = int(l[1:3], 16)

      if (slen == 0x00):
        continue

      addr = int(l[3:7], 16)
      frmt = l[7:9]

      if ( not frmt == "00" ):
        print("ERROR: Not I8HEX formatting.")
        sys.exit(-1)


      for b in range(0, slen, 2):

        bytelo = int(l[9+((b+0)*2):11+((b+0)*2)], 16)
        bytehi = int(l[9+((b+1)*2):11+((b+1)*2)], 16)

        SetAddr( fd, addr+b >> 1 )

        fd.write("c%c" % chr(bytelo))
        fd.flush()
        if (fd.read(1) != '\r'):
          print "ERROR: Write not acknowleged."
          sys.exit(-1)

        fd.write("C%c" % chr(bytehi))
        fd.flush()
        if (fd.read(1) != '\r'):
          print "ERROR: Write not acknowleged."
          sys.exit(-1)

        SetAddr( fd, addr+b >> 1 )

        fd.write("m")
        fd.flush()
        if (fd.read(1) != '\r'):
          print "ERROR: Flash page not acknowleged."
          sys.exit(-1)

    TermProgress( float( addr+b ) / float( alen ), None, None )

  TermProgress( 1.0, None, None )

  print

  fl.close()


def main():

  if (len(sys.argv)<3):
    print "Usage: %s -op read|write|erase -start <0x0000> -stop <0x1FFFF> -file intel.hex <-serial /dev/ttyUSB0> <-baud 19200>" % (sys.argv[0])
    sys.exit(-1)

  baud = 19200
  command = ""
  memstart = 0x0000
  memstops = 0x0000
  filename = sys.argv[2]
  serialln = "/dev/ttyUSB0"


  for i in range(1, len(sys.argv), 2):

    if ( sys.argv[i] == "-op" ):
      command = sys.argv[i+1]
      continue
    elif ( sys.argv[i] == "-file" ):
      filename = sys.argv[i+1]
      continue
    elif ( sys.argv[i] == "-start" ):
      memstart = int(sys.argv[i+1],16)
      continue
    elif ( sys.argv[i] == "-stop" ):
      memstops = int(sys.argv[i+1],16)
      continue
    elif ( sys.argv[i] == "-baud" ):
      baud = int(sys.argv[i+1])
      continue
    elif ( sys.argv[i] == "-serial" ):
      serialln = sys.argv[i+1]
      continue
    else:
      print ("UNKNOWN option %s" % sys.argv[i])
      sys.exit(-1)

  fd = serial.Serial (serialln, baudrate = baud, bytesize = serial.EIGHTBITS, stopbits = serial.STOPBITS_ONE, parity = serial.PARITY_NONE)
  fd.reset_input_buffer()
  fd.reset_output_buffer()
  fd.flush()

  GetParams( fd )

  if (command == "read"):
    if (memstops-memstart < 1):
      print ("ERROR: Memory range invalid.")
      sys.exit(-1)
    ReadPGMMem( fd, "dump.hex", memstart, memstops )

  elif (command == "write"):
    BurnHexFile( fd, filename )

  elif (command == "erase"):
    EraseFlash( fd )

  else:
    print ("UNKNOWN command %s" % command)
    sys.exit(-1)

  fd.close()


if __name__ == "__main__":
    main()
