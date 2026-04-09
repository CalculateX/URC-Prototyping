from flask import Flask, render_template, request, jsonify
import serial
import threading
import re
import time
import pygame
import keyboard

app = Flask(__name__)
SERIAL_PORT = 'COM19' 
BAUD_RATE = 9600

# INITIAL STATE
rover_data = {
    "m1": 0.0, "m2": 0.0, "m3": 0.0, "m4": 0.0, "m5": 0.0, "m6": 0.0,
    "cmd_l": 0.0, "cmd_r": 0.0,
    "led_color": "OFF",
    "power_limit": 0.0,
    "mode": "DRIVE",
    "s1": 1500.0, "s2": 1500.0, "s3": 1500.0, "s4": 1500.0,
    "sci_cmd": "N",
    "neo7": 0.0, "neo8": 0.0  # Added NEO states
}

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print(f"Connected to Radio on {SERIAL_PORT}")
except:
    ser = None
    print("MOCK MODE: No Radio.")

# --- KEYBOARD WORKER (SCIENCE W/A/S/D) ---
def keyboard_worker():
    global rover_data
    while True:
        try:
            if keyboard.is_pressed('w'): rover_data["sci_cmd"] = 'U'
            elif keyboard.is_pressed('s'): rover_data["sci_cmd"] = 'D'
            elif keyboard.is_pressed('d'): rover_data["sci_cmd"] = 'R'
            elif keyboard.is_pressed('a'): rover_data["sci_cmd"] = 'L'
            else: rover_data["sci_cmd"] = 'N'
        except: pass
        time.sleep(0.05)

threading.Thread(target=keyboard_worker, daemon=True).start()

# --- TELEMETRY WORKER ---
def telemetry_worker():
    global rover_data
    pattern = re.compile(r"M1:(?P<m1>[\d\.]+),M2:(?P<m2>[\d\.]+),M3:(?P<m3>[\d\.]+),M4:(?P<m4>[\d\.]+),M5:(?P<m5>[\d\.]+),M6:(?P<m6>[\d\.]+)")
    while True:
        if ser and ser.is_open:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                match = pattern.search(line)
                if match:
                    for i in range(1, 7): rover_data[f"m{i}"] = float(match.group(f"m{i}"))
            except: pass
        time.sleep(0.01)

threading.Thread(target=telemetry_worker, daemon=True).start()

# --- CONTROLLER & RADIO TRANSMIT WORKER ---
def controller_worker():
    global rover_data
    pygame.init(); pygame.joystick.init()
    has_joy = pygame.joystick.get_count() > 0
    joy = pygame.joystick.Joystick(0) if has_joy else None
    if joy: joy.init()
    
    power_limit = 0.0; lb_down, rb_down = False, False
    btn_a_down, btn_b_down, btn_x_down = False, False, False
    current_led_char = 'O' 

    while True:
        if joy:
            pygame.event.pump()
            
            # Global LED Controls
            if joy.get_button(1) and not btn_b_down:
                current_led_char, rover_data["led_color"] = ('O', "OFF") if rover_data["led_color"] == "RED" else ('R', "RED")
                btn_b_down = True
            elif not joy.get_button(1): btn_b_down = False
            if joy.get_button(0) and not btn_a_down:
                current_led_char, rover_data["led_color"] = ('O', "OFF") if rover_data["led_color"] == "GREEN" else ('G', "GREEN")
                btn_a_down = True
            elif not joy.get_button(0): btn_a_down = False
            if joy.get_button(2) and not btn_x_down:
                current_led_char, rover_data["led_color"] = ('O', "OFF") if rover_data["led_color"] == "BLUE" else ('B', "BLUE")
                btn_x_down = True
            elif not joy.get_button(2): btn_x_down = False

            if rover_data["mode"] == "DRIVE":
                # Power Limit Controls (Only active in drive mode)
                if joy.get_button(5) and not rb_down: power_limit = min(1.0, power_limit + 0.10); rb_down = True
                elif not joy.get_button(5): rb_down = False
                if joy.get_button(4) and not lb_down: power_limit = max(0.0, power_limit - 0.10); lb_down = True
                elif not joy.get_button(4): lb_down = False
                rover_data["power_limit"] = power_limit

                # 1. Base Throttle from Triggers
                rt = (joy.get_axis(5) + 1) / 2
                lt = (joy.get_axis(4) + 1) / 2
                throttle = rt - lt
                
                # 2. Independent Side Controls from Sticks
                raw_ly = -joy.get_axis(1)
                raw_ry = -joy.get_axis(3)
                
                # Apply a 5% deadzone to prevent stick drift
                ly = raw_ly if abs(raw_ly) > 0.05 else 0.0
                ry = raw_ry if abs(raw_ry) > 0.05 else 0.0
                
                # 3. Combine Throttle + Independent Sticks
                bl = throttle + ly
                br = throttle + ry
                
                # 4. Normalize (Ensure we never command more than 100% power)
                max_val = max(abs(bl), abs(br), 1.0)
                bl /= max_val
                br /= max_val
                
                # 5. Apply Power Limit AND Global Hardware Inversion
                rover_data["cmd_l"] = -br * power_limit
                rover_data["cmd_r"] = -bl * power_limit
                
                # Lock NEOs in Drive Mode
                rover_data["neo7"], rover_data["neo8"] = 0.0, 0.0

            elif rover_data["mode"] == "ARM":
                # In Science mode, drive motors are locked to 0
                rover_data["cmd_l"], rover_data["cmd_r"] = 0.0, 0.0
                
                # Existing Servo mapping
                analog = 40.0
                if abs(joy.get_axis(0)) > 0.15: rover_data["s1"] += joy.get_axis(0) * analog
                if joy.get_axis(5) > -0.5: rover_data["s2"] += ((joy.get_axis(5)+1)/2)*analog
                if joy.get_axis(4) > -0.5: rover_data["s2"] -= ((joy.get_axis(4)+1)/2)*analog
                if abs(joy.get_axis(2)) > 0.15: rover_data["s3"] += joy.get_axis(2) * analog
                if abs(joy.get_axis(3)) > 0.15: rover_data["s4"] += joy.get_axis(3) * analog
                for s in ["s1", "s2", "s3", "s4"]: rover_data[s] = max(500, min(2500, rover_data[s]))
                
                # NEW: NEO 7 mapping (Bumpers: RB is forward, LB is reverse at 50% speed)
                if joy.get_button(5): rover_data["neo7"] = 0.2
                elif joy.get_button(4): rover_data["neo7"] = -0.2
                else: rover_data["neo7"] = 0.0
                
                # NEW: NEO 8 mapping (Face Buttons: Y is forward, A is reverse at 50% speed)
                if joy.get_button(3): rover_data["neo8"] = 0.2
                elif joy.get_button(0): rover_data["neo8"] = -0.2
                else: rover_data["neo8"] = 0.0

        if ser and ser.is_open:
            m_char = 'D' if rover_data["mode"] == "DRIVE" else 'A'
            # Radio String now has 11 segments
            msg = f"<{m_char},{rover_data['cmd_l']:.2f},{rover_data['cmd_r']:.2f},{int(rover_data['s1'])},{int(rover_data['s2'])},{int(rover_data['s3'])},{int(rover_data['s4'])},{current_led_char},{rover_data['sci_cmd']},{rover_data['neo7']:.2f},{rover_data['neo8']:.2f}>\n"
            ser.write(msg.encode())
        
        # 10Hz Rate Limiter to prevent radio choke
        time.sleep(0.1)

threading.Thread(target=controller_worker, daemon=True).start()

# --- FLASK ROUTES ---
@app.route('/api/set_mode/<mode>')
def set_mode(mode):
    global rover_data
    if mode in ["DRIVE", "ARM"]: rover_data["mode"] = mode
    return jsonify({"status": "ok"})

@app.route('/')
def index(): return render_template('manual.html')

@app.route('/api/telemetry')
def get_telemetry(): return jsonify(rover_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)