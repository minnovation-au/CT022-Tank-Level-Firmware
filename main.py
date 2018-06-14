################## Start setup (EDIT START HERE)

SITE = 'SRCL'
key = b'alphaxencryptkeysjtwbutfdchdlcec' # 256 bit (32 bytes) key

################## End setup (EDIT END HERE)

import socket, os, pycom, crypto, socket, gc, machine, utime, ubinascii, ustruct
from machine import SD, WDT, deepsleep, Pin, Timer
from network import LoRa, WLAN
from crypto import AES
from uModBus.serial import Serial
from uModBus.tcp import TCP

iv = crypto.getrandbits(128) # hardware generated random IV (never reuse it)

gc.enable()
wdt = WDT(timeout=4000000)
adc = machine.ADC()

# Turn off WiFi to save power
w = WLAN()
#w.deinit()

chrono = Timer.Chrono()
chrono.start()

volt = adc.channel(pin='P20')

pycom.heartbeat(False)
pycom.rgbled(0x007f00) # Turn on Green LED

def getVoltage():
    val = volt()/4095*4.2
    return(val)

print(getVoltage())

def getPressure():
    uart_id = 0x01
    modbus_obj = Serial(uart_id, pins=('P10', 'P9'))

    slave_addr=1
    starting_address=62594
    register_quantity=1
    signed=True
    result=''

    for y in range(0,2):
        try:
            register_value = modbus_obj.read_holding_registers(slave_addr, starting_address, register_quantity, signed)
            #print(register_value)
            #print(bytes(register_value[1]))
            result = ustruct.unpack('>f', register_value)
            #print(result[0])
            #print(result[1]-14.7)
        except Exception as e:
            pass
        utime.sleep(1)
    return(result[0])

def aggregate():
    try:
        pycom.nvs_set('val', int(pycom.nvs_get('val'))+1)
    except:
        pycom.nvs_set('val', 0)
    print('Deepsleep Remaining: '+str(machine.remaining_sleep_time()))
    print('New Aggregate: '+str(pycom.nvs_get('val')))
    print('Current Message ID: '+str(pycom.nvs_get('msgID')))

def ammend_to_file():
    try:
        f = open('/flash/log.txt', 'r')
        lines = f.readlines()
        f.close()
        lines=lines[1:]
        print(lines[-20:-1])
        f = open('/flash/log.txt', 'w')
        for a in range (0,999):
            try:
                f.write(lines[a])
            except:
                f.write('\n')
        f.close()
    except:
        pass
    f = open('/flash/log.txt', 'a')
    f.write(str(pycom.nvs_get('msgID')))
    f.write(',')
    f.write(str(pycom.nvs_get('val')))
    f.write('\n')
    f.close()

def mac():
    mac=ubinascii.hexlify(machine.unique_id(),':').decode()
    mac=mac.replace(":","")
    return(mac)
print(mac())

def encrypt(send_pkg):
    cipher = AES(key, AES.MODE_CFB, iv)
    send_pkg = iv + cipher.encrypt(send_pkg)
    return(send_pkg)

def decrypt(recv_pkg):
    cipher = AES(key, AES.MODE_CFB, recv_pkg[:16]) # on the decryption side
    recv_pkg = cipher.decrypt(recv_pkg[16:])
    return(recv_pkg)

def LoRaSend(val):
    
    sl.setblocking(True)
    sl.send(encrypt(SITE+mac()+'&'+val)) # Send on LoRa Network & wait Reply
    sl.setblocking(False)

    #chrono.reset()
    #recv_pkg=''
    #while (recv_pkg != mac()):
        #recv_pkg = sl.recv(48)
        #if (len(recv_pkg) > 2):
            #recv_pkg = decrypt(recv_pkg).decode('utf-8')
        #if (chrono.read_ms() > 2000):
            #print('Packet Dropped')
            #machine.pin_deepsleep_wakeup(pins=['P10'], mode=machine.WAKEUP_ANY_HIGH )
            #machine.deepsleep(600000)
            #return
    #print('Send Success')
    #ammend_to_file()
    #pycom.nvs_set('val', 0)
    #try:
        #pycom.nvs_set('msgID', int(pycom.nvs_get('msgID'))+1)
    #except:
        #pycom.nvs_set('msgID', 0)

pycom.rgbled(0) # Turn on Green LED
lora = LoRa(mode=LoRa.LORA, region=LoRa.AU915, power_mode=LoRa.TX_ONLY)
sl = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
LoRaSend('{"val":'+str(getPressure())+',"volt":'+str(getVoltage())+',"msgID":'+str(lora.stats()[8])+'}')
print('Send: {"val":'+str(getPressure())+',"volt":'+str(getVoltage())+',"msgID":'+str(lora.stats()[8])+'}')
lora = LoRa(mode=LoRa.LORA, region=LoRa.AU915, power_mode=LoRa.SLEEP)
print(getPressure())
print('Sleeping')
wdt.feed()
#machine.deepsleep(3600000)
