#!/usr/bin/python

#   ____       _           _   _  _   _    
#  / ___|     | |__   ___ | |_| || | | | __
# | |  _ _____| '_ \ / _ \| __| || |_| |/ /
# | |_| |_____| |_) | (_) | |_|__   _|   < 
#  \____|     |_.__/ \___/ \__|  |_| |_|\_\
#                                                  
# A program to read GPS data and capture to a file
#(c) Graham Blackwell, GDMA Technology Ltd
#v7  wait for hat board to be turned on, then commence logging
#v8  when hat board turned off, close the open files and exit program.
#    Log raw nmea data to dbg file.
#    Send nmea sentence string just before capture begins, to turn on vtg,gga,rmc (was being ignored)
#v9  Removed illegal colon chars from generated filename to allow files to be copied using Explorer
#    Epoch calculation error fixed
#    Created write_kml_header routine
#v10 Shutdown Pi and power off when HAT turned off
#v11 Fixed gga.timestamp string length
#    Added number of satellites to output file gps.num_sats
#v12 Using the I2C interface, read analogue voltages from the AB Electronics Pi ADC
#v13 Read the ADC channels between the data arriving from the gps hat

import serial, time, pynmea2, os, datetime, calendar, sys
from ADCPi import ADCPi

#write the kml header to the kml file
def write_kml_header():
    h.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n") 
    h.write("<kml xmlns=\"http://www.opengis.net/kml/2.2\" xmlns:atom=\"http://www.w3.org/2005/Atom\">\n")
    h.write(" <Document>\n")
    h.write("  <name>G-Bot4K KML file</name>\n")
    h.write("  <description>Experimental data captured using Pi3 and Waveshare GPS HAT</description>\n")
    h.write("  <atom:author>\n")
    h.write("   <atom:name>Graham Blackwell</atom:name>\n")
    h.write("  </atom:author>\n")
    h.write("  <Style id=\"yellowPoly\">\n")
    h.write("  <LineStyle>\n")
    h.write("   <color>7f00ffff</color>\n")
    h.write("   <width>4</width>\n")
    h.write("  </LineStyle>\n")
    h.write("  <PolyStyle>\n")
    h.write("   <color>7f00ff00</color>\n")
    h.write("  </PolyStyle>\n")
    h.write("  </Style>\n")
    h.write("   <Placemark><styleUrl>#yellowPoly</styleUrl>\n")
    h.write("   <name>G-Bot4k gps data " + opfilename + "</name>\n")
    h.write("   <LineString>\n")
    h.write("   <extrude>1</extrude>\n")
    h.write("   <tessellate>1</tessellate>\n")
    h.write("   <altitudeMode>absolute</altitudeMode>\n")
    h.write("    <coordinates>\n")

#                             ____ ____  ____  
#  _ __   __ _ _ __ ___  ___ / ___|  _ \/ ___| 
# | '_ \ / _` | '__/ __|/ _ \ |  _| |_) \___ \ 
# | |_) | (_| | |  \__ \  __/ |_| |  __/ ___) |
# | .__/ \__,_|_|  |___/\___|\____|_|   |____/ 
# |_|
#this is the section where the data is captured from the initialised gps module,
#parsed, then saved to a file on the microSD card
def parseGPS(str):
    degWhole=0
    lat_deg=0
    lon_deg=0
    if 'NORMAL POWER DOWN' in str: #user has pressed the power button to turn off the HAT, so shutdown
        print "NORMAL POWER DOWN rxd, closing files, Pi can be powered off safely"
        close_down() #close all files and exit the application
    if 'GGA' in str:
        msg = pynmea2.parse(str)
        #andrew needs epoch time added to the log file
        #assuming we succesfully reset the Pi's system time to the gps time earlier.....
        curTime = "%s" %(time.time()) #get Epoch time and store as a string, with a trailing zero
        epoch_time= curTime.replace(".","") #get the pi's system time and convert in to epoch time
        if len(epoch_time)<12: epoch_time += "0"
        if len(msg.lon) >0:
            lon = float(msg.lon) #turn the string in to a float
            degWhole=int(lon/100) #find the whole degree part
            degDec = (lon - degWhole*100)/60 #find the fractional part
            lon_deg = degWhole + degDec #complete correct decimal form
            if msg.lon_dir == 'W': #if Western hemisphere, lon degs should be -ve
                lon_deg = -1 * lon_deg
        if len(msg.lat) >0:
            lat = float(msg.lat) #turn the string in to a float
            degWhole=int(lat/100) #find the whole degree part
            degDec = (lat - degWhole*100)/60 #find the fractional part
            lat_deg = degWhole + degDec #complete correct decimal form
            if msg.lat_dir == 'S': #if Southern hemisphere, lat degs should be -ve
                lat_deg = -1 * lat_deg
        ggaTStamp = "%.10s" % (msg.timestamp)
        if len(ggaTStamp) < 10: ggaTStamp = ggaTStamp + ".0"
        gga_data = "%s,%s,%s,%s,%s,%s,%s,%s,%s," % (epoch_time,ggaTStamp,msg.gps_qual,msg.num_sats,msg.lat,msg.lat_dir,msg.lon,msg.lon_dir,msg.altitude)
        g.write(gga_data,)
        h.write("%s,%s,%s " % (lon_deg,lat_deg,msg.altitude))
    if 'VTG' in str:
        msg= pynmea2.parse(str)
        vtg_data = "%s,%s\n" % (msg.spd_over_grnd_kmph,msg.true_track) #gpsSpeed, gpsCourse
        g.write(vtg_data)

#                     _                                      _   
#  _ __ ___  __ _  __| |    ___  ___ _ __   _ __   ___  _ __| |_ 
# | '__/ _ \/ _` |/ _` |   / __|/ _ \ '__| | '_ \ / _ \| '__| __|
# | | |  __/ (_| | (_| |   \__ \  __/ |    | |_) | (_) | |  | |_ 
# |_|  \___|\__,_|\__,_|___|___/\___|_|____| .__/ \___/|_|   \__|
#                     |_____|        |_____|_| 
def read_ser_port():
    global data
    while ser.inWaiting() > 0:
        data = ser.readline()
    print data
    
#                     _               _ 
#  _ __ ___  __ _  __| |     __ _  __| | ___ 
# | '__/ _ \/ _` |/ _` |    / _` |/ _` |/ __|
# | | |  __/ (_| | (_| |   | (_| | (_| | (__
# |_|  \___|\__,_|\__,_|___ \__,_|\__,_|\___|
#                     |_____|
def read_adc():
    #global adcCh1, adcCh2, adcCh3, adcCh4
    curTime = "%s" %(time.time()) #get Epoch time and store as a string, with a trailing zero
    epoch_time= curTime.replace(".","") #get the pi's system time and convert in to epoch time
    if len(epoch_time)<12: epoch_time += "0"
    adcCh1 = "%02f" % (adc.read_voltage(1)) #read ch1 from A-D 1
    adcCh2 = "%02f" % (adc.read_voltage(5)) #read ch1 from A-D 2
    adcCh3 = "%02f" % (adc.read_voltage(2)) #read ch2 from A-D 1
    adcCh4 = "%02f" % (adc.read_voltage(6)) #read ch2 from A-D 2
    #write the adc data to the output file
    op = "%s,%s,%s,%s,%s\n" % (epoch_time,adcCh1,adcCh2,adcCh3,adcCh4)
    i.write(op) #write the four adc channels to the output file

#       _                       _                     
#   ___| | ___  ___  ___     __| | _____      ___ __  
#  / __| |/ _ \/ __|/ _ \   / _` |/ _ \ \ /\ / / '_ \ 
# | (__| | (_) \__ \  __/  | (_| | (_) \ V  V /| | | |
#  \___|_|\___/|___/\___|___\__,_|\___/ \_/\_/ |_| |_|
#                      |_____|
def close_down():
    ser.write("AT+CGNSPWR=0\r\n") #turn the HAT off
    f.close() #close the gps debug file
    g.flush()
    g.close() #close the gps log file
    h.write("    </coordinates>\r\n")
    h.write("   </LineString>\r\n")
    h.write("  </Placemark>\r\n")
    h.write(" </Document>\r\n")
    h.write("</kml>\n")
    h.flush()
    h.close() #close the gps kml file
    i.flush()
    i.close()
    sys.exit("Done")
    #os.system('sudo shutdown -h now')

#  _       _ _                       
# (_)_ __ (_) |_      __ _ _ __  ___ 
# | | '_ \| | __|    / _` | '_ \/ __|
# | | | | | | |_    | (_| | |_) \__ \
# |_|_| |_|_|\__|____\__, | .__/|___/
#              |_____|___/|_|
def init_gps():
    init_buff = ["AT+CGNSPWR=1\r\n", "AT+CGNSCMD=0,\"$PMTK101*32\"\r\n", "AT+CGNSURC=1\r\n", "AT+CGNSTST=1\r\n"]
    init_expl = ["HAT Powering on",  "HAT Hot start", "Display unsolicited Result Code","Send data rxd from UART1 to UART2"]
    for i in range(0,4): #send all the init codes to the HAT module to set it up
        print "G-Bot4k: %s" %(init_expl[i])
        ser.write(init_buff[i])
        time.sleep(0.25)
        read_ser_port()

#  _       _ _                _      
# (_)_ __ (_) |_     __ _  __| | ___ 
# | | '_ \| | __|   / _` |/ _` |/ __|
# | | | | | | |_   | (_| | (_| | (__ 
# |_|_| |_|_|\__|___\__,_|\__,_|\___|
#              |_____|                 
def init_adc():
    global adc
    adc = ADCPi(0x68, 0x69, 12)
    adc.set_conversion_mode(1) #1 = continuous conversion
    #12 = 12 bit (240SPS max)
    #14 = 14 bit (60SPS max)
    #16 = 16 bit (15SPS max)
    #18 = 18 bit (3.75SPS max)
    
#  _       _ _                       
# (_)_ __ (_) |_      __ _ _ __  _ __ ___ 
# | | '_ \| | __|    / _` | '_ \| '__/ __|
# | | | | | | |_    | (_| | |_) | |  \__ \
# |_|_| |_|_|\__|____\__, | .__/|_|  |___/
#              |_____|___/|_|
def init_gprs():
    print "gprs: Turn off gps output"
    ser.write("AT+CGNSPWR=0\r\n") #turn off gps hat
    time.sleep(0.5)
    ser.write("AT+CGNSPWR=1\r\n") #turn on gps hat
    time.sleep(0.5)
    read_ser_port()
    print "gprs: Query the gprs card for signal quality"
    ser.write("AT+CSQ\r\n") #query the gprs card for signal quality
    time.sleep(1)
    read_ser_port()
    print "gprs: Phone signal quality is ";data
    ser.write("AT+CSTT=/'giffgaff.com/'") #set network to giffgaff
    time.sleep(1)
    read_ser_port()
    ser.write("AT+CREG?\r\n") #query the gprs car for network registration
    read_ser_port()
    if data.find(',1') or data.find(',5'):
        print "G-Bot4k: Network Registration successful"
    ser.write("AT+CGATT=1\r\n") #Attach to the network
    read_ser_port()   
    ser.write("AT+CGATT?\r\n") #Query the GPRS attachment (is the device attached to the network)
    read_ser_port()
    #ser.write("AT+CIICR\r\n") #Bring up wireless connection with GPRS
    #read_ser_port()
    #ser.write("AT+CGPADDR=1\r\n") #Get an ip address
    #read_ser_port()
    #ser.write("AT+CISFR\r\n") #Get local ip address
    #read_ser_port()
    #ser.write("AT+CIPCLOSE\r\n") #Close TCP or UDP connection
    #read_ser_port


#                _ _        __                    _   
# __      ____ _(_) |_     / _| ___  _ __    __ _| |_ 
# \ \ /\ / / _` | | __|   | |_ / _ \| '__|  / _` | __|
#  \ V  V / (_| | | |_    |  _| (_) | |    | (_| | |_ 
#   \_/\_/ \__,_|_|\__|___|_|  \___/|_|_____\__,_|\__|
#                    |_____|         |______|    
#wait for the HAT to reply to an AT command eg it is powered on
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

#      _             _   
#  ___| |_ __ _ _ __| |_ 
# / __| __/ _` | '__| __|
# \__ \ || (_| | |  | |_ 
# |___/\__\__,_|_|   \__|
#
ser = serial.Serial("/dev/ttyS0",115200)
ser.flushInput()
ser.flushOutput()
ser.timeout = 1

os.system('clear') #cls
print "G-Bot4k: Waiting for HAT to respond OK to AT probe"
wait_for_at() #sit and wait for the GPS board to respond before continuing
#init_gprs()   #get the board ready for sending data over that t'internet
init_adc()    #initialise the ADC
init_gps()    #initialise the GPS board

data = ""
print "G-Bot4k: Reading data from the GPS module (ctrl-c to abort)"
qual = 0
print "G-Bot4k: Waiting for gps_quality >0 (this can take a couple of minutes, be patient)"
print ">>> Press ctrl-c to abort <<<"
#startup, wait for the gps_qual !="0"
while qual != 1:
    str = ser.readline()
    if str.find('GGA') > 0:
        msg=pynmea2.parse(str)
        print msg.gps_qual,
        if msg.gps_qual != 0:
            qual = 1
            print "\nG-Bot4k: gps_qual Established "
            print "G-Bot4k: Selecting update frequency of 10Hz"
            ser.write("AT+CGNSCMD=0,\"$PMTK220,100*2F\"\r\n")
            time.sleep(1)
            while ser.inWaiting() > 0:
                data = ser.readline()
            print data

#lets get the time and date from the RMC NMEA string (as the RTC on the Pi doesnt have battery backup)
gpsDate = ""
while gpsDate == "":
    str = ser.readline()
    if str.find('RMC') >0: 
        msg=pynmea2.parse(str)
        gpsDate = msg.datestamp
        gpsTime = msg.timestamp
        gpsutc = "%sT%sZ" % (gpsDate,gpsTime)
        os.system('sudo date -u --set="%s"' % gpsutc) #Set the Pi time to the gps time

#create the save file filename by using the gps date and time
str = "capture_%.10s-%.8s" % (gpsDate,gpsTime)
opfilename = str.replace(":","-",3) #The time contains colons, so we need to remove the colons from the file name
print "G-Bot4k: now capturing NMEA data to log file\n"+os.getcwd() + "/" + opfilename + "\n"
print "Press ctrl-c to abort"

#open both save files for write
g = open("/home/pi/" + opfilename+".txt","w") #this is the destination txt file
h = open("/home/pi/" + opfilename+".kml","w") #this is the destination kml file
write_kml_header() #write all the xml header info in to the kml file
f = open("/home/pi/" + opfilename+".dbg","w") #this is the destination nmea raw file for debugging
g.write("/home/pi/" + opfilename+".txt\n")
print "G-Bot4k: Saving to /home/pi/" + opfilename
g.write("G-Bot4k gps data capture test at 10Hz\r\n")
g.write("epochTime,gpsTime,gpsQual,gpsNumsats,gpsLat,gpsLatDir,gpsLon,gpsLonDir,gpsAltitude,gpsSpeed(kph),gpsCourse\n")
i = open("/home/pi/" + opfilename+".adc.txt","w")
i.write("G-Bot4k adc data capture test at 50Hz\r\n")
i.write("epochTime,adcCh1,adcCH2,adcCh3,adcCh4\n")

#Turn on just the three NMEA sentences we need, VTG, GGA and RMC
ser.write("AT+CGNSCMD=0,\"$PMTK314,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*29\"\r\n")
time.sleep(0.5)
#now lets loop around reading in the gps data over ttyS0 and saving to file
str = ser.readline()
while True:
    #so the gps data is being produced at 10Hz, and the ADC data is being parsed at the same time
    #so if we insert an additional read_adc() we'll get ADC at 20Hz and gps at 10Hz
    str = ser.readline()
    parseGPS(str)
    f.write(str) #write the nmea string to the debug file
    read_adc() #get the adc data for the four channels, and write to the log file







