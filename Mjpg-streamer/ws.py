# -*- coding:utf-8 -*-
import os
import sys
import json
import time
import tornado.httpserver
import tornado.web
import tornado.ioloop
import thread
from tornado import websocket
import random
import uuid
import sys
import serial
reload(sys)
sys.setdefaultencoding('utf-8')
listenPort=8888
currentPressure=123
currentDepth=50
currentAngle=45
lastSpeedH=0
mega=serial.Serial("/dev/ttyACM0",115200)
def read_sensor_mpu6050():
    mega.write("{d}")
    time.sleep(0.1)
    timeWait=0
    while(mega.inWaiting()==0):
        time.sleep(0.1)
        if(timeWait==5):
            print "time out"
            return ['0','0','0']
        timeWait=timeWait+1
    tmp=mega.read(mega.inWaiting())
    #print tmp
    if(tmp[0]!="{" or tmp[-3]!="}"):return (-1,-1,-1)
    tmp=tmp[1:-3]
    try:
        tmp=tmp.split(",")
        x=tmp[0]
        y=tmp[1]
        z=tmp[2]
    except:
        x='-1'
        y='-1'
        z='-1'
    return (x,y,z)

def read_sensor_ms5803():
    mega.write("{e,f}")
    time.sleep(0.1)
    tmp=mega.read(mega.inWaiting())
    #print tmp
    try:
        tmp=tmp.split("\r\n")
        pressure=tmp[0][1:-1]
        temperature=tmp[1][1:-1]
    except:
        temperature="-1"
        pressure="-1"
    return (temperature,pressure)

def read_volts():
    mega.write("{g}")
    time.sleep(0.1)
    tmp=mega.read(mega.inWaiting())
    #print tmp
    try:
        tmp=tmp.split("\r\n")
        volts=tmp[0][1:-1]
    except:
        volts="0"
    return (volts)


def attach_motor():
    #mega.write("A")
    pass

def motor_init():
    mega.write("{B}")
    

def motorV(speed):
    command="{m1:"+str(speed)+",m2:"+str(speed)+"}"
    mega.write(command)
    
def setTargetDepth(targetDepthNum):
    command="{h:"+targetDepthNum+"}"
    mega.write(command)

def motorH(speed):
    command="{m3:"+str(speed)+",m4:"+str(speed)+"}"
    mega.write(command)
   

def motorH2(speedL,speedR):
    command="{m3:"+str(speedL)+",m4:"+str(speedR)+"}"
    mega.write(command)
    
def turnOnLight():
    mega.write('{i:1}')

def turnOffLight():
    mega.write('{i:0}')

def startPid():
    turnOnLight()
    #mega.write("{t}")

def stopPid():
    turnOffLight()
    #mega.write("{t}")

def dataTransfer():
    global currentPressure
    global currentDepth
    global currentAngle
    while True:
        result1=read_sensor_ms5803()
        time.sleep(0.8)
        result2=read_sensor_mpu6050()
        time.sleep(0.1)
        result3=read_volts()
        currentVolts=result3
        currentPressure=result1[1]
        currentDepth=int(float(currentPressure)/500)
        currentTemp=result1[0]
        currentAngleX=result2[0]
        currentAngleY=result2[1]
        currentAngleZ=result2[2]
        dataToSend={}
        dataToSend['pressure']=currentPressure
        dataToSend['depth']=currentDepth
        dataToSend['anglex']=currentAngleX
        dataToSend['angley']=currentAngleY
        dataToSend['anglez']=currentAngleZ
        dataToSend['temperature']=currentTemp
        dataToSend['volts']=currentVolts
        #msg="{'presure':'"+str(presure1)+"','depth':'"+str(depth1)+"','angle':'"+str(angle1)+"'}"
        msg=json.dumps(dataToSend)
        print "Send ",msg
        SocketHandler.send_to_all(msg)
        time.sleep(0.8)


class SocketHandler(tornado.websocket.WebSocketHandler):
    clients = set()

    def check_origin(self, origin):  
        return True

    @staticmethod
    def send_to_all(message):
        for c in SocketHandler.clients:
            c.write_message(message)

    def open(self):
        SocketHandler.clients.add(self)
        self.write_message("{'presure':'123','depth':'23.5','angle':'90'}")
        print "new connection build"

    def on_message(self, message):
        global lastSpeedH
        print "Recv:",message
        data=json.loads(message)
        dataType=data['type']
        dataContent=data['content']
        if(dataType=="SpeedControlZ"):
            speedNum=int(dataContent)
            if(speedNum>500):
                speedNum=500
            motorV(speedNum)
            print "Z axis speed set to ",speedNum
        elif(dataType=="SpeedControlY"):
            speedNum=int(dataContent)
            if(speedNum>500):
                speedNum=500
            lastSpeedH=speedNum
            motorH(speedNum)
            print "Y axis speed set to ",speedNum
        elif(dataType=="Roll"):
            rollRate=int(dataContent)
            speedLeft=lastSpeedH+rollRate/3
            speedRight=lastSpeedH-rollRate/3
            if(speedLeft>500):speedLeft=500
            if(speedLeft<0):speedLeft=0
            if(speedRight>500):speedRight=500
            if(speedRight<0):speedRight=0
            motorH2(speedLeft,speedRight)
            print "Roll ",speedLeft,speedRight
        elif(dataType=="targetDepth"):
            targetDepthNum=int(dataContent)
            if(targetDepthNum>1200):speedNum=1200
            if(targetDepthNum<1000):targetDepthNum=1000
            setTargetDepth(targetDepthNum)
            print "Target depth set to ",targetDepthNum
        elif(dataType=="Attach"):
            attach_motor()
            print "Motor attach"
        elif(dataType=="InitMotor"):
            motor_init()
            print "Motor init"
        elif(dataType=="LedControl"):
            ledState=dataContent
            if(ledState=="k"):
                turnOnLight()
                print "Led turned on"
            else:
                turnOffLight()
                print "Led turned off"
        elif(dataType=="Pid"):
            pidState=dataContent
            if(pidState=="k"):
                #turnOnLight()
                startPid()
                print "Start pid"
            else:
                #turnOffLight()
                stopPid()
                print "Stop pid"
        elif(dataType=="PowerControl"):
            powerState=dataContent
            if(powerState=="g"):
                print "Turn down power"
            else:
                print "Turn on power"
        else:
            print "Unknow data type"


if __name__ == '__main__':
    app = tornado.web.Application([
        ('/soc', SocketHandler)
    ],cookie_secret='abcd',
    template_path=os.path.join(os.path.dirname(__file__), "template"),
    static_path=os.path.join(os.path.dirname(__file__), "template"),
    )
    print "Running"
    thread.start_new_thread(dataTransfer,())
    app.listen(listenPort)
    tornado.ioloop.IOLoop.instance().start()
    mega.close()
