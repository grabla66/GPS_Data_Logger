#!/usr/bin/python

#   ____       _           _   _  _   _    
#  / ___|     | |__   ___ | |_| || | | | __
# | |  _ _____| '_ \ / _ \| __| || |_| |/ /
# | |_| |_____| |_) | (_) | |_|__   _|   < 
#  \____|     |_.__/ \___/ \__|  |_| |_|\_\
#                                                  
# A program to read GPS data and capture to a file
#(c) Graham Blackwell, GDMA Technology Ltd

#v18 cache last five samples when stopped so when moved the speed starts from zero
#v19c fixed more shit :D

import serial, time, pynmea2, os, datetime, calendar, sys
from ADCPi import ADCPi #AB Electronics A-D library

#                             ____ ____  ____  
#  _ __   __ _ _ __ ___  ___ / ___|  _ \/ ___| 
# | '_ \ / _` | '__/ __|/ _ \ |  _| |_) \___ \ 
# | |_) | (_| | |  \__ \  __/ |_| |  __/ ___) |
# | .__/ \__,_|_|  |___/\___|\____|_|   |____/ 
# |_|
#
def parseGPS(str):
    global vmax, hatPower, vtg_data,vehicle, filesOpen
    global gga_data,gga5,gga4,gga3,gga2,gga1,vtg5,vtg4,vtg3,vtg2,vtg1
    degWhole=0
    lat_deg=0
    lon_deg=0
    if 'NORMAL POWER DOWN' in str: #user has pressed the power button to turn off the HAT, so shutdown
        #print "NORMAL POWER DOWN rxd, closing files, shutting down Pi."
        hatPower = 0
    if 'GGA' in str:
        #try:
            msg = pynmea2.parse(str)
            curTime = "%s" %(time.time()) #get Epoch time and store as a string, with a trailing zero
            epoch_time= curTime.replace(".","") #get the pi's system time and convert in to epoch time
            if len(epoch_time)<12: epoch_time += "0"
            ggaTStamp = "%.10s" % (msg.timestamp)
            if len(ggaTStamp) < 10: ggaTStamp = ggaTStamp + ".0"
            gga_data = "%s,%s,%s,%s,%s,%s,%s,%s,%s," % (epoch_time,ggaTStamp,msg.gps_qual,msg.num_sats,msg.lat,msg.lat_dir,msg.lon,msg.lon_dir,msg.altitude)
            if filesOpen ==1:
                gpsFile.write(gga_data,)
                gpsFile.write(vtg_data)            
            if filesOpen ==0:
                gga5=gga4 #cache the gga data whilst there is no open file to write to
                gga4=gga3
                gga3=gga2
                gga2=gga1
                gga1=gga_data
            #h.write("%s,%s,%s " % (lon_deg,lat_deg,msg.altitude))
        #except:
            #print "GGA Parse Error skipped",str
            
    if 'VTG' in str:
        #try:
            msg= pynmea2.parse(str)
            vtg_data = "%s,%s\n" % (msg.spd_over_grnd_kmph,msg.true_track) #gpsSpeed, gpsCourse
            #if float(msg.spd_over_grnd_kmph) > 0.0:
            #    print vtg_data
            if filesOpen ==0:
                vtg5=vtg4 #cache the vtg data whilst there is no open file to write to
                vtg4=vtg3
                vtg3=vtg2
                vtg2=vtg1
                vtg1=vtg_data
            if "%s" % (msg.spd_over_grnd_kmph) > vmax: vmax = "%s" % (msg.spd_over_grnd_kmph)
            if float(msg.spd_over_grnd_kmph) == 0.0:
                if vehicle == "moving":
                    vehicle = "stopped" #vehicle has come to a halt
            if float(msg.spd_over_grnd_kmph) > 0.0:
                if vehicle == "stopped":
                    vehicle = "moving" #vehicle has started moving again
        #except:
            #print "VTG Parse Error skipped",str
            

def read_ser_port(): #grab whatever data is waiting and return in the 'data' variable
    global data
    #sit and wait for serial data before returning
    while ser.inWaiting() > 0:
        data = ser.readline()


def read_adc():
    global i #i is the adc filename
    #this subroutine is only called if the filesOpen=1
    curTime = "%s" %(time.time()) #get Epoch time and store as a string, with a trailing zero
    epoch_time= curTime.replace(".","") #get the pi's system time and convert in to epoch time
    if len(epoch_time)<12: epoch_time += "0"
    adcCh1 = "%02f" % (adc.read_voltage(1)) #read ch1 from A-D 1
    adcCh2 = "%02f" % (adc.read_voltage(5)) #read ch1 from A-D 2
    adcCh3 = "%02f" % (adc.read_voltage(2)) #read ch2 from A-D 1
    adcCh4 = "%02f" % (adc.read_voltage(6)) #read ch2 from A-D 2
    #write the adc data to the output file
    op = "%s,%s,%s,%s,%s\n" % (epoch_time,adcCh1,adcCh2,adcCh3,adcCh4)
    adcFile.write(op) #write the four adc channels to the output file
    #if filesOpen == 0:
    #    adc5=adc4
    #    adc4=adc3
    #    adc3=adc2
    #    adc2=adc1
    #    adc1=op

def close_down():
    #sendCmdToSerPort("AT+CGNSPWR=0\r\n","OK",2) #turn the HAT off
    #f.close() #close the gps debug file
    global gps,adc,filesOpen
    if filesOpen == 1:
        gpsFile.flush() #flush the gps log file
        gpsFile.close() #close the gps log file
        adcFile.flush() #flush the adc csv file
        adcFile.close() #close the adc csv file
    #sys.exit("Done")
    os.system('sudo shutdown -h now')

def closeFiles():
    global gps,adc,filesOpen
    print "G-Bot4k: closeFiles(): Flushing and closing all open files"
    gpsFile.flush() #flush the gps log file
    gpsFile.close() #close the gps log file
    adcFile.flush() #flush the adc csv file
    adcFile.close() #close the adc csv file
    filesOpen = 0 #we have no open files


def openFiles():
    global gpsFile,adcFile,fpath, opfilename,filesOpen
    fpath = "/media/usb/"
    gpsFile = open(fpath + opfilename+".log.csv","w") #this is the destination txt file
    gpsFile.write(fpath + opfilename+".log.csv\n")
    gpsFile.write("epochTime,gpsTime,gpsQual,gpsNumsats,gpsLat,gpsLatDir,gpsLon,gpsLonDir,gpsAltitude,gpsSpeed(kph),gpsCourse\n")
    adcFile = open(fpath + opfilename+".adc.csv","w")
    adcFile.write(fpath + opfilename+".adc.csv\n")
    adcFile.write("epochTime,adcCh1,adcCh2,adcCh3,adcCh4\n")
    filesOpen = 1 #we have open files ;)
    print "G-Bot4k: openFiles(): Opening new files " + fpath + opfilename


def init_gps():
    init_buff = ["AT+CGNSPWR=1",  "AT+CGNSURC=1", "AT+CGNSTST=1","AT+CFUN=4"] #"AT+CGNSCMD=0,\"$PMTK101*32\"" <= Dont do hot start as it upsets speed
    init_expl = ["HAT Powering on",  "Turn on navigation data URC report","Send data received from GNSS to AT UART","Flight mode"] #"HAT Hot start"
    for i in range(0,4): #send all the init codes to the HAT module to set it up
        print "G-Bot4k: %s" %(init_expl[i])
        sendCmdToSerPort(init_buff[i],"OK",2)


def init_adc():
    global adc
    adc = ADCPi(0x68, 0x69, 12)
    adc.set_conversion_mode(1) #1 = continuous conversion
    #12 = 12 bit (240SPS max)
    #14 = 14 bit (60SPS max)
    #16 = 16 bit (15SPS max)
    #18 = 18 bit (3.75SPS max)
    

def sendCmdToSerPort(serCmd,retCode,tOut):
    found = 0
    while found == 0:
        print "G-Bot4k: sendCmdToSerPort: sending " + serCmd + "& waiting for " + retCode
        ser.write(serCmd.strip("\r\n") + "\r\n")
        sTime=time.time() #get the time
        #wait a time interval (tOut, in seconds), then timeout if return code not received
        while found == 0 and time.time() < sTime + tOut: #while the time is <2s ticks since the start.... 
            #time.sleep(0.5)
            str = ser.readline()
            if retCode in str: #if the return string is found in the string sent back from the HAT, then exit with a 1
                print str #.strip("\r\n")
                found =1
                return 1 #all good


#wait for the HAT to reply to an AT command, eg wait for it to be powered on
def wait_for_at():
    awake = 0
    while awake == 0:
        ser.write("AT\r\n")
        time.sleep(0.5)
        while ser.inWaiting() > 0:
            str = ser.readline()
            if 'OK' in str:
                awake=1
                print "OK"


def initSerial():
    global ser
    ser.flushInput()
    ser.flushOutput()
    ser.timeout = 1



def setFilename():
    #capture_2018-02-16-08-30-10
    #use the system date&time to set the filename, rather than the GPS, which requires wasting an NMEA string
    global opfilename
    print "G-Bot4k: Getting System date and time to set the output filename"
    now = datetime.datetime.now()
    gpsDate = now.strftime("%Y-%m-%d")
    gpsTime = now.strftime("%H-%M-%S")
    opfilename = "capture_%.10s-%.8s" % (gpsDate,gpsTime)


#main loop here
ser = serial.Serial("/dev/ttyS0",115200)
initSerial    #initialise the serial port
filesOpen=0
vehicle = "stopped"
vmax = 0
hatPower = 0
qual = 0
os.system('clear') #clear the console screen

print "G-Bot4k: Waiting for HAT to respond OK to AT probe"
wait_for_at() #Poll the GPS board for it to respond to an AT code before continuing
init_adc()    #initialise the ADC
init_gps()    #initialise the GPS board
hatPower = 1  #the HAT is now on!
data = ""

print "G-Bot4k: Waiting for gps_quality >0 (this can take a couple of minutes, be patient)"
print ">>> Press ctrl-c to abort <<<"
#sendCmdToSerPort("AT+CGNSCMD=0,\"$PMTK314,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*29\"\r\n","OK",2)

#startup, wait for the gps_qual !="0"
while qual != 1:
    str = ser.readline()
    if 'GGA' in str:
        print str
        try:
            msg=pynmea2.parse(str)
            if msg.gps_qual != 0:
                qual = 1
                print "\nG-Bot4k: gps_qual Established "
                print "G-Bot4k: Setting update frequency to 10Hz"
                sendCmdToSerPort("AT+CGNSCMD=0,\"$PMTK220,100*2F\"","OK",2)
        except:
            print "Parse Error waiting for satellite quality, skipped"

print "G-Bot4k: Setting system time to gps time"
#Get the time and date from the RMC NMEA string & set the Pi clock to use it
gpsDate = ""
while gpsDate == "":
    str = ser.readline()
    if 'RMC' in str: 
        try:
            msg=pynmea2.parse(str)
            gpsDate = msg.datestamp
            gpsTime = msg.timestamp
            gpsutc = "%sT%sZ" % (gpsDate,gpsTime)
            os.system('sudo date -u --set="%s"' % gpsutc) #Set the Pi time to the gps time
            os.system('sudo mount /dev/sda1 /media/usb -o uid=pi,gid=pi') #mount the usb drive
            print gpsutc
        except:
            print "Parse Error getting RMC to set time & date, skipped"
            

#now create the save file filename by using the gps date and time
str = "capture_%.10s-%.8s" % (gpsDate,gpsTime)
opfilename = str.replace(":","-",3) #The time contains colons, so we need to remove the colons from the file name

#Turn on just the three NMEA sentences we need, VTG, GGA and RMC
sendCmdToSerPort("AT+CGNSCMD=0,\"$PMTK314,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*29\"\r\n","OK",2)

ser.flushInput()  #flush the serial buffer
ser.flushOutput() #flush the serial buffer

gga5=""
vtg5=""
gga4=""
vtg4=""
gga3=""
vtg3=""
gga2=""
vtg2=""
gga1=""
vtg1=""
gga_data=""
vehicle = "stopped"

#loop around reading in the gps data over ttyS0 and saving to file
#str = ser.readline()
print "G-Bot4k: Capturing GPS data, filesOpen =",filesOpen,", vehicle is",vehicle

while hatPower == 1:
    str = ser.readline() #read a line of text from the serial bufer
    parseGPS(str)  #get the NMEA string, decode, and write to the log file
    if filesOpen == 1:
        read_adc()     #get the adc data for the four channels, and write to the log file
    if vehicle == "stopped":
        if filesOpen == 1:
            print "G-Bot4k: Vehicle has stopped"
            str = ser.readline() #read a line of text from the serial bufer
            parseGPS(str)
            closeFiles()
            filesOpen = 0
    if vehicle == "moving":
        if filesOpen == 0:
            print "G-Bot4k: Vehicle has moved, writing cached data to file"
            setFilename() #create output filename using gps time from last time read
            openFiles()
            filesOpen = 1
            if gga5 <> "":
                gpsFile.write(gga5,)
                gpsFile.write(vtg5)
            if gga4 <> "":
                gpsFile.write(gga4,)
                gpsFile.write(vtg4)
            if gga3 <> "":
                gpsFile.write(gga3,)
                gpsFile.write(vtg3)
            if gga2 <> "":
                gpsFile.write(gga2,)
                gpsFile.write(vtg2)
            if gga1 <> "":
                gpsFile.write(gga1,)
                gpsFile.write(vtg1)
                gga5=""
                vtg5=""
                gga4=""
                vtg4=""
                gga3=""
                vtg3=""
                gga2=""
                vtg2=""
                gga1=""
                vtg1=""

print "Now closing files and shutting down"
close_down() #close all files and exit the application
