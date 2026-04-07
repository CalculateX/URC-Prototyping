import serial
import time
import ctypes
import os
import struct
import socket




# CONFIGURATION
CURRENT_SCALE = 2048.0
VOLTAGE_SCALE = 512.0
LEFT_SIDE_IDS = [1, 2, 3]
RIGHT_SIDE_IDS = [4, 5, 6]




RADIO_PORT = '/dev/ttyUSB0'
RADIO_BAUD = 9600




ARDUINO_PORTS = [
'/dev/ttyCH341USB0',
'/dev/ttyCH341USB1',
]
ARDUINO_BAUD = 9600




# SECTION 1: SYSTEM INITIALIZATION




print("\n[INIT] Configuring CAN interface...")
os.system("/sbin/ip link set can1 down")
time.sleep(0.1)
os.system("/sbin/ip link set can1 up type can bitrate 1000000 restart-ms 100")
time.sleep(0.1)




print("[INIT] Initializing Spark Max Bridge...")
lib = None
try:
lib = ctypes.CDLL("/home/urc/sparkcan/build/libspark_bridge.so")
for mid in LEFT_SIDE_IDS + RIGHT_SIDE_IDS:
    lib.init_motor(b"can1", mid)
print(" -> 6 Motors Initialized.")
except Exception as e:
print(f" -> BRIDGE ERROR: {e}")
print("    (Motor control will fail, but LEDs might still work)")




# Connect to Arduinos (LEDs and Arm)
print("[INIT] Searching for Arduinos...")
arduinos = []
for port in ARDUINO_PORTS:
try:
    candidate = serial.Serial(port, ARDUINO_BAUD, timeout=1)
    arduinos.append(candidate)
    print(f" -> Arduino FOUND on {port}")
except: pass




if not arduinos:
print(" -> WARNING: Arduinos not found. LEDs and Arm will not function.")
else:
time.sleep(2)




print("[INIT] Connecting to Radio...")
ser = None
try:
ser = serial.Serial(RADIO_PORT, RADIO_BAUD, timeout=0.1)
print(f" -> Radio Connected on {RADIO_PORT}")
except:
print(" -> WARNING: No Radio Found. Rover is in passive mode.")




can_sock = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
try:
can_sock.bind(('can1',))
can_sock.setblocking(False)
print("[INIT] Telemetry Listener Active.")
except Exception as e:
print(f" -> SOCKET ERROR: {e}")




# SECTION 2: RUNTIME VARIABLES
mode_flag = 'D'
left_power = 0.0
right_power = 0.0
last_packet_time = time.time()
last_telemetry_time = time.time()
motor_data = { mid: {'amps': 0.0} for mid in LEFT_SIDE_IDS + RIGHT_SIDE_IDS }




def parse_telemetry(can_id, data):
if len(data) < 8: return
device_id = can_id & 0x3F
api_id = (can_id >> 6) & 0x3FF
if api_id == 0x2E0:
    raw_curr = struct.unpack('<h', data[0:2])[0]
    if device_id in motor_data:
        motor_data[device_id]['amps'] = abs(raw_curr / CURRENT_SCALE)




print("\n--- ROVER SYSTEMS ONLINE ---")




# SECTION 3: MAIN LOOP
try:
while True:
    try:
        while True:
            frame = can_sock.recv(16)
            can_id, can_dlc, data = struct.unpack("<IB3x8s", frame)
            parse_telemetry(can_id & 0x1FFFFFFF, data)
    except BlockingIOError: pass




    if ser and ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith('<') and line.endswith('>'):
                parts = line[1:-1].split(',')
            
                # Now expecting 8 pieces of data from the laptop
                if len(parts) >= 8:
                    mode_flag = parts[0].strip()
                    left_power = float(parts[1])
                    right_power = float(parts[2])
                    s1 = int(float(parts[3]))
                    s2 = int(float(parts[4]))
                    s3 = int(float(parts[5]))
                    s4 = int(float(parts[6]))
                    led_cmd = parts[7].strip()
                    last_packet_time = time.time()
                
                    if arduinos:
                        # Format: R<1500,1500,1500,1500>
                        ard_msg = f"{led_cmd}<{s1},{s2},{s3},{s4}>\n"
                        for ard in arduinos:
                            try:
                                ard.write(ard_msg.encode())
                            except: pass
                    
        except ValueError: pass




    if time.time() - last_packet_time > 0.5:
        left_power = 0.0
        right_power = 0.0




    if lib:
        if mode_flag == 'D':
            # Standard Drive Mode (All 6 wheels)
            l_final = left_power * 1.0
            for mid in LEFT_SIDE_IDS:
                lib.set_power(mid, ctypes.c_float(l_final))
        
            r_final = right_power * -1.0
            for mid in RIGHT_SIDE_IDS:
                lib.set_power(mid, ctypes.c_float(r_final))
             
        elif mode_flag == 'A':
            # Arm Mode (Route to 1 and 4, lock the rest)
            lib.set_power(1, ctypes.c_float(left_power))
            lib.set_power(4, ctypes.c_float(right_power))
         
            lib.set_power(2, ctypes.c_float(0.0))
            lib.set_power(3, ctypes.c_float(0.0))
            lib.set_power(5, ctypes.c_float(0.0))
            lib.set_power(6, ctypes.c_float(0.0))




    if time.time() - last_telemetry_time > 0.1:
        packet_data = []
        for i in sorted(motor_data.keys()):
            packet_data.append(f"M{i}:{motor_data[i]['amps']:.2f}")
    
        packet_str = "[" + ",".join(packet_data) + "]\n"
    
        if ser:
            ser.write(packet_str.encode('utf-8'))
    
        last_telemetry_time = time.time()




    time.sleep(0.01)




except KeyboardInterrupt:
print("\n[SHUTDOWN] Stopping...")
finally:
if lib:
    for mid in LEFT_SIDE_IDS + RIGHT_SIDE_IDS:
        lib.set_power(mid, ctypes.c_float(0.0))
if 'arduinos' in globals():
    for ard in arduinos:
        ard.close()
os.system("/sbin/ip link set can1 down")
