# Imports
import sys
import subprocess
import re
import math
import time
import sqlite3 as lite
import getopt
import json
from pprint import pprint

sys.path.append('/home/pi/share/assets')
from Adafruit_CharLCD import * 


# constants and globals
gFollowICAO='XX'
gFollowDist=99.9
gDidSnap=0
gFileBase=' '
cRadiusOfEarth = 6371;
cFeetToKm = 0.0003048
gSQLDBStandingDBLocn='/home/pi/share/sqllite/StandingData.sqb'
gSQLDBBaseStnDBLocn='/home/pi/share/sqllite/BaseStation.sqb'
fLogFileDest='/home/pi/share/log/piplanepicture.txt'
fLogPicDest='/home/pi/share/pic/'
# Where I live
cHomeLat1=-30.1234
cHomeLon1=150.1234
myICAOArray = {}
myFlightArray = {} 
 
def formNumber (pInputText):
    try:
        return float(pInputText.replace('\r', ''))
    except:
        return float(0)
 
def formText (pInputText):
    return pInputText.replace('\r', '')
 
def movePanTilt(pBearing, pAzimuth):
    # Bigger numbers closer to E, smaller numbers closer to W
    # E-240, S-152, W-64
    servBrgValue = 330 - (pBearing * 177/180)
    
    # Bigger numbers closer to horizon, smaller numbers closer to sky
    # 150-horizon, sky-70
    servAzmValue = 150 - (pAzimuth * 85/90)
    file_f = open('/dev/servoblaster', 'w')
    file_f.write("0=" + str(servAzmValue) + "\n")
    file_f.write("1=" + str(servBrgValue) + "\n")
    file_f.close()

def storeAndRefineICAOandCode(pICAO, pFlightCode):
    # Found ICAO and flight code, now store
    if myICAOArray.has_key(pICAO):
        # alreaded cached, drop out
        return

    myICAOArray[pICAO] = pFlightCode
    myFlightArray[pICAO] = ["", "", "", "", ""]
    con = lite.connect(gSQLDBStandingDBLocn)
    with con:    
        cur = con.cursor()    
        cur.execute("SELECT FROMAIRPORTLOCATION, TOAIRPORTLOCATION, OPERATORICAO FROM ROUTEVIEW WHERE CALLSIGN  = ?  ", (pFlightCode,))
        rows = cur.fetchall()
        for row in rows:
            myFlightArray[pICAO][0] = row[0]
            myFlightArray[pICAO][1] = row[1]
            myFlightArray[pICAO][2] = row[2]
    
    con = lite.connect(gSQLDBBaseStnDBLocn)
    with con:    
        cur = con.cursor()    
        cur.execute("SELECT ICAOTYPECODE, REGISTRATION FROM AIRCRAFT WHERE MODES = UPPER(?) ", (pICAO,))
        rows = cur.fetchall()
        for row in rows:
            myFlightArray[pICAO][3] = row[0]
            myFlightArray[pICAO][4] = row[1]
    

def getFlightCodeDtls (pICAO):
    if myICAOArray.has_key(pICAO) and myFlightArray.has_key(pICAO):
        return myICAOArray[pICAO] + " " +  myFlightArray[pICAO][1] + " " + myFlightArray[pICAO][2] + " " + myFlightArray[pICAO][3] + " " + myFlightArray[pICAO][4]
    elif myICAOArray.has_key(pICAO) :
        return myICAOArray[pICAO] + " (no flight detals) " 
    else:
        return "ICAO:" + pICAO + " (no other details)" 

def printFlightCodeDtls (pICAO):
    vFlightStr = getFlightCodeDtls (pICAO)
    print "========================================================================"
    print vFlightStr
    lcd.clear()
    lcd.message(vFlightStr[:16] + '\n' + vFlightStr[16:])
    print "========================================================================"

def doSnapOfFlight (pICAO, pDist, pBearing, pAlt, pAzm):
    print "*** SNAP *** SNAP *** SNAP *** SNAP *** SNAP *** SNAP ***"
    # doCameraSnap()
    printFlightCodeDtls(pICAO) 
    if myICAOArray.has_key(pICAO) and myFlightArray.has_key(pICAO):
        vFile = open(fLogFileDest, "a")
        vFile.write(time.strftime("%d/%m/%Y %H:%M:%S ") + "\n" )
        vFile.write("  ICAO:" + pICAO + "\n" )
        vFile.write("  Code:" + myICAOArray[pICAO]  + "\n" )
        vFile.write("  From:" + myFlightArray[pICAO][0]  + "\n" )
        vFile.write("  Dest:" + myFlightArray[pICAO][1]  + "\n" )
        vFile.write("  ArLn:" + myFlightArray[pICAO][2]  + "\n" )
        vFile.write("  Type:" + myFlightArray[pICAO][3]  + "\n" )
        vFile.write("  Rego:" + myFlightArray[pICAO][4]  + "\n" )
        vFile.write("  Dist:" + str(round(pDist,2))  + "\n" )
        vFile.write("  Brng:" + str(round(pBearing,0))  + "\n" )
        vFile.write("  Altd:" + str(pAlt)  + "\n" ) 
        vFile.write("  Azmt:" + str(round(pAzm,0))  + "\n" )
        vFile.write( "\n" )
        vFile.close        
    print "*** SNAP *** SNAP *** SNAP *** SNAP *** SNAP *** SNAP ***"

def doWriteJSON (pFileBase, pICAO, pDist, pBearing, pAlt, pAzm):
    vFileName = pFileBase + '.json'
    print "JSON file " + vFileName
    if myICAOArray.has_key(pICAO) and myFlightArray.has_key(pICAO):
        lv_infoarray = {}
        lv_infoarray['DATE'] = time.strftime("%d/%m/%Y %H%M")
        lv_infoarray['ICAO'] = pICAO
        lv_infoarray['CODE'] = myICAOArray[pICAO]
        lv_infoarray['FROM'] = myFlightArray[pICAO][0]
        lv_infoarray['DEST'] = myFlightArray[pICAO][1]
        lv_infoarray['ARLN'] = myFlightArray[pICAO][2]
        lv_infoarray['TYPE'] = myFlightArray[pICAO][3]
        lv_infoarray['REGO'] = myFlightArray[pICAO][4]
        lv_infoarray['DIST'] = str(round(pDist,2))
        lv_infoarray['BRNG'] = str(round(pBearing,0))
        lv_infoarray['ALTD'] = str(pAlt)
        lv_infoarray['AZMT'] = str(round(pAzm,0))
        with open(vFileName, mode='w') as f_file:
            json.dump(lv_infoarray, f_file)     
 

def doCameraSnap() :
    vFileName = fLogPicDest + time.strftime("%Y%m%d_%H%M%S") + '.jpg'
    print "Photo file " + vFileName
    p1 = subprocess.call(['/usr/bin/raspistill', '-t', '2', '-o',  vFileName])
 
def doCameraVideo(pFileBase) :
    vFileName = pFileBase + '.h264'
    print "Video file " + vFileName
    p1 = subprocess.Popen(['/usr/bin/raspivid', '-w', '960', '-h', '540', '-t', '40000', '-o',  vFileName])
 
def processSquark (pICAO, pFeet, pLatitude, pLongitude):
    global gFollowICAO
    global gFollowDist
    global gDidSnap
    global gFileBase

    if pLatitude==0 or pLongitude==0:
        # Bad inputs
        return
        
    lat2=pLatitude
    lon2=pLongitude
     
    f1 = math.radians(cHomeLat1);
    f2 = math.radians(lat2);
    delta_f = math.radians(lat2-cHomeLat1);
    delta_g = math.radians(lon2-cHomeLon1);
    a = math.sin(delta_f/2) * math.sin(delta_f/2) +  math.cos(f1) * math.cos(f2) *    math.sin(delta_g/2) * math.sin(delta_g/2);
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a));
    dist_km = cRadiusOfEarth * c;
    brng_r=math.atan2(
      math.sin(lon2-cHomeLon1) * math.cos(lat2)
    , math.cos(cHomeLat1)*math.sin(lat2)-math.sin(cHomeLat1)*math.cos(lat2)*math.cos(lon2-cHomeLon1)
    )
     
    brng_d=(360.0 - math.degrees(brng_r))%360.0
    azmth=math.degrees(math.atan(pFeet*cFeetToKm / dist_km))
    
    if dist_km < 7 and brng_d>160 and brng_d<270 and int(time.strftime("%H")) < 19:
        # This squark is close and within sweep of servo and is before 7PM
        
        if brng_d<230 and gFollowICAO <> pICAO:
            # This is new and approaching from the right direction, show some details and start video record
            printFlightCodeDtls(pICAO) 
            gFollowDist=99.9
            gDidSnap=0
            gFileBase = fLogPicDest + time.strftime("%Y%m%d_%H%M%S")
            doCameraVideo(gFileBase)
        gFollowICAO = pICAO
        
        if dist_km > gFollowDist and gDidSnap==0:
            # beginning to get further away now
            doSnapOfFlight (pICAO, dist_km, brng_d, pFeet, azmth)
            doWriteJSON (gFileBase, pICAO, dist_km, brng_d, pFeet, azmth)
            gDidSnap=1
        gFollowDist = dist_km
            
        
            
        print "  " + time.strftime("%H:%M:%S " ) + " (" + pICAO + ") Dist:" + str(round(dist_km,2)) + "(km) Bearing:" + str(round(brng_d,0)) + " Alt:" + str(pFeet) + "(ft) azm:" + str(round(azmth,0))
        if brng_d>160 and brng_d<270 and azmth>0 and azmth<90:
            movePanTilt(brng_d, azmth) 

################################################################################ 
# Setup
textblock = ''
vDebugMode = 0
vSnapMode = 0
vManualBrg=-1
vManualAzm=-1

try:
    opts, args = getopt.getopt(sys.argv[1:],"sda:b:", ["snap", "debug", "azimuth=", "bearing="] )
except getopt.GetoptError:
    print 'piplanepicture.py [-s|--snap] [-d|--debug] [-a XX|--azimuth=XX] [-b YY|--bearing=YY]'
    sys.exit(2)
for opt, arg in opts:
    if opt in ('-d', '--debug') :
        vDebugMode = 1
    elif opt in ('-s', '--snap') :
        vSnapMode = 1
    elif opt in ('-a', '--azimuth'):
        vManualAzm = arg
    elif opt in ('-b', '--bearing'):
        vManualBrg = arg


if vManualBrg != -1 and vManualAzm != -1:
    print '*** MANUAL SERVO MODE ***'
    print "vManualBrg:" + vManualBrg
    print "vManualAzm:" + vManualAzm
    movePanTilt(formNumber(vManualBrg), formNumber(vManualAzm))
    if vSnapMode == 1:
        doCameraSnap()
    sys.exit(2)
 
if vSnapMode == 1:
    doCameraSnap()
    sys.exit(2)

if vDebugMode == 0: 
    sproc = subprocess.Popen('/home/pi/dump1090/dump1090', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
else:
    print '*** DEBUG MODE ***'
    sproc = subprocess.Popen('cat /home/pi/test/dump1090_test2.txt', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)



lcd = Adafruit_CharLCD()
lcd.clear()
lcd.message("Started at " + time.strftime("%H:%M" ))

################################################################################ 
# Begin main read loop
while True: 
    if vDebugMode == 1: 
        time.sleep(.001)

    line = sproc.stdout.readline()

    textblock = textblock + line
    
    if len(line) == 1:
        # Start of block of info
        searchICAO = re.search( r'(ICAO Address   : )(.*$)', textblock, re.M|re.I)
        searchFeet = re.search( r'(Altitude : )(.*)(feet)(.*$)', textblock, re.M|re.I)
        searchLatitude = re.search( r'(Latitude : )(.*$)', textblock, re.M|re.I)
        searchLongitude = re.search( r'(Longitude: )(.*$)', textblock, re.M|re.I)
        searchIdent = re.search( r'(Identification : )(.*$)', textblock, re.M|re.I)

        if searchICAO and searchIdent:
            valICAO = formText(searchICAO.group(2))
            valIdent = formText(searchIdent.group(2)).strip()
            storeAndRefineICAOandCode(valICAO, valIdent)
 
        if searchFeet and searchICAO and searchLatitude and searchLongitude:
            # Found a valid combination 
            valICAO = formText(searchICAO.group(2))
            valFeet = formNumber(searchFeet.group(2))
            valLatitude = formNumber(searchLatitude.group(2))
            valLongitude = formNumber(searchLongitude.group(2))
            processSquark (valICAO, valFeet, (valLatitude), (valLongitude))
 
        # End of block of info
        textblock = ''
    # End of read of line

retval = sproc.wait()

    
