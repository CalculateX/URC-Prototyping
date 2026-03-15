import socket
import struct
import time
import ctypes

# --- CONFIGURATION ---
MOTOR_ID = 3
TEST_POWER = 0.50
GEAR_RATIO = 45.0  

try:
    lib = ctypes.CDLL("/home/urc/sparkcan/build/libspark_bridge.so")
    lib.init_motor(b"can1", MOTOR_ID)
except Exception as e:
    print(f"Bridge error: {e}")
    exit(1)

can_sock = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
can_sock.bind(('can1',))
can_sock.setblocking(False)

print(f"\nMotor {MOTOR_ID} Live Telemetry")
print("Reading Status 0 (Volts/Amps) and Status 2 (RPM/Pos)...")
time.sleep(1)

last_print = time.time()
current_amps = 0.0
bus_voltage = 0.0
joint_rpm = 0.0
joint_pos = 0.0

try:
    while True:
        # Feed the hardware watchdog continuously
        lib.set_power(MOTOR_ID, ctypes.c_float(TEST_POWER))

        try:
            while True:
                frame = can_sock.recv(16)
                can_id_raw, _, data = struct.unpack("<IB3x8s", frame)
                
                can_id = can_id_raw & 0x1FFFFFFF
                device_id = can_id & 0x3F
                api_id = (can_id >> 6) & 0x3FF

                if device_id == MOTOR_ID:
                    
                    # Status 0: Voltage and Current (Firmware v24+)
                    if api_id == 0x2E0 and len(data) >= 8:
                        # Bytes 4-5: Bus Voltage
                        raw_volts = struct.unpack('<H', data[4:6])[0]
                        bus_voltage = raw_volts / 512.0
                        
                        # Bytes 2-3: Current is packed into the LOWER 12 bits
                        raw_curr_word = struct.unpack('<H', data[2:4])[0]
                        raw_curr_12 = raw_curr_word & 0x0FFF
                        
                        # Hardware zero-point is ~1667. 32 LSB = 1 Amp.
                        current_amps = abs(raw_curr_12 - 1667) / 32.0
                        
                    # Status 2: Velocity and Position (Firmware v24+)
                    elif api_id == 0x2E2 and len(data) >= 8:
                        raw_rpm = struct.unpack('<f', data[0:4])[0]
                        raw_pos = struct.unpack('<f', data[4:8])[0]
                        
                        joint_rpm = raw_rpm / GEAR_RATIO
                        joint_pos = raw_pos / GEAR_RATIO
                        
        except BlockingIOError:
            pass
        
        # Print cleanly at 10Hz
        if time.time() - last_print > 0.1:
            print(f"Volts: {bus_voltage:>5.2f} V | Amps: {current_amps:>5.2f} A | RPM: {joint_rpm:>7.2f} | POS: {joint_pos:>7.2f} Rot")
            last_print = time.time()
            
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    lib.set_power(MOTOR_ID, ctypes.c_float(0.0))


