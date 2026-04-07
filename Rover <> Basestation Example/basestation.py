# Commands to Upload to GitHub
# Open Git Bash
# git status (see what items modified)
# git add -p (or "git add ." for everything)
# git commit -m "write your message here"
# git push

from flask import Flask, render_template, request, jsonify
import serial
import threading
import re
import time
import pygame

app = Flask(__name__)
SERIAL_PORT = 'COM19' 
BAUD_RATE = 9600

# INITIAL STATE: 0% Power for safety
rover_data = {
    "m1": 0.0, "m2": 0.0, "m3": 0.0, "m4": 0.0, "m5": 0.0, "m6": 0.0,
    "cmd_l": 0.0, "cmd_r": 0.0,
    "led_color": "OFF",
    "power_limit": 0.0,
    "mode": "DRIVE",
    "s1": 1500.0, "s2": 1500.0, "s3": 1500.0, "s4": 1500.0
}

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print(f"Connected to Radio on {SERIAL_PORT}")
except:
    ser = None
    print("MOCK MODE: No Radio.")

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

def controller_worker():
    global rover_data
    pygame.init()
    pygame.joystick.init()
    
    if pygame.joystick.get_count() == 0: return
    joy = pygame.joystick.Joystick(0)
    joy.init()
    
    power_limit = 0.0 
    
    lb_down, rb_down = False, False
    btn_a_down, btn_b_down, btn_x_down = False, False, False
    current_led_char = 'O' 

    while True:
        pygame.event.pump()
        
        # --- POWER LIMITER ---
        if joy.get_button(5) and not rb_down: # RB
            power_limit = min(1.0, power_limit + 0.10)
            rb_down = True
        elif not joy.get_button(5): rb_down = False

        if joy.get_button(4) and not lb_down: # LB
            power_limit = max(0.0, power_limit - 0.10)
            lb_down = True
        elif not joy.get_button(4): lb_down = False
        
        rover_data["power_limit"] = power_limit

        # --- LED TOGGLE LOGIC ---
        if joy.get_button(1) and not btn_b_down: # B
            if rover_data["led_color"] == "RED":
                current_led_char = 'O'; rover_data["led_color"] = "OFF"
            else:
                current_led_char = 'R'; rover_data["led_color"] = "RED"
            btn_b_down = True
        elif not joy.get_button(1): btn_b_down = False

        if joy.get_button(0) and not btn_a_down: # A
            if rover_data["led_color"] == "GREEN":
                current_led_char = 'O'; rover_data["led_color"] = "OFF"
            else:
                current_led_char = 'G'; rover_data["led_color"] = "GREEN"
            btn_a_down = True
        elif not joy.get_button(0): btn_a_down = False

        if joy.get_button(2) and not btn_x_down: # X
            if rover_data["led_color"] == "BLUE":
                current_led_char = 'O'; rover_data["led_color"] = "OFF"
            else:
                current_led_char = 'B'; rover_data["led_color"] = "BLUE"
            btn_x_down = True
        elif not joy.get_button(2): btn_x_down = False

        # --- MODE MIXING ---
        if rover_data["mode"] == "DRIVE":
            raw_rt = (joy.get_axis(5) + 1) / 2.0
            raw_lt = (joy.get_axis(4) + 1) / 2.0
            raw_turn = joy.get_axis(2)

            if raw_rt < 0.05: raw_rt = 0.0
            if raw_lt < 0.05: raw_lt = 0.0
            if abs(raw_turn) < 0.1: raw_turn = 0.0

            throttle = raw_rt - raw_lt
            
            base_l = -throttle + raw_turn
            base_r = -throttle - raw_turn

            # --- ASYMMETRIC TURNING LOGIC ---
            if raw_turn < 0: 
                # Turning left: double the left side power
                base_l *= 0.5
            elif raw_turn > 0: 
                # Turning right: double the right side power
                base_r *= 0.5

            # Clamp the final outputs to the power limit
            rover_data["cmd_l"] = max(-1.0, min(1.0, base_l * power_limit))
            rover_data["cmd_r"] = max(-1.0, min(1.0, base_r * power_limit))

        elif rover_data["mode"] == "ARM":
            analog_speed = 40.0 

            # NEO 1 -> Left Joystick Y
            rover_data["cmd_l"] = -joy.get_axis(1) * power_limit
            
            # NEO 2 -> D-Pad Up/Down
            if joy.get_numhats() > 0:
                hat_y = joy.get_hat(0)[1]
                rover_data["cmd_r"] = hat_y * power_limit
            else:
                try:
                    if joy.get_button(12): rover_data["cmd_r"] = power_limit
                    elif joy.get_button(13): rover_data["cmd_r"] = -power_limit
                    else: rover_data["cmd_r"] = 0.0
                except: 
                    rover_data["cmd_r"] = 0.0

            # Servo 1 (Turntable) -> Left Joystick X
            if abs(joy.get_axis(0)) > 0.15: 
                rover_data["s1"] += joy.get_axis(0) * analog_speed

            # Servo 2 (Gripper) -> Triggers
            rt = joy.get_axis(5)
            lt = joy.get_axis(4)
            if rt > -0.5: rover_data["s2"] += ((rt + 1.0) / 2.0) * analog_speed
            if lt > -0.5: rover_data["s2"] -= ((lt + 1.0) / 2.0) * analog_speed

            # Servo 3 (End Effector) -> Right Joystick X
            if abs(joy.get_axis(2)) > 0.15: 
                rover_data["s3"] += joy.get_axis(2) * analog_speed

            # Servo 4 (Wrist Pitch) -> Right Joystick Y
            if abs(joy.get_axis(3)) > 0.15: 
                rover_data["s4"] += joy.get_axis(3) * analog_speed

            # Clamp servos safely
            rover_data["s1"] = max(500, min(2500, rover_data["s1"]))
            rover_data["s2"] = max(500, min(2500, rover_data["s2"]))
            rover_data["s3"] = max(500, min(2500, rover_data["s3"]))
            rover_data["s4"] = max(500, min(2500, rover_data["s4"]))

        if ser and ser.is_open: 
            try:
                m_char = 'D' if rover_data["mode"] == "DRIVE" else 'A'
                msg = f"<{m_char},{rover_data['cmd_l']:.2f},{rover_data['cmd_r']:.2f},{int(rover_data['s1'])},{int(rover_data['s2'])},{int(rover_data['s3'])},{int(rover_data['s4'])},{current_led_char}>\n"
                ser.write(msg.encode())
            except: pass
            
        time.sleep(0.05) 

threading.Thread(target=controller_worker, daemon=True).start()

@app.route('/api/set_mode/<mode>')
def set_mode(mode):
    global rover_data
    if mode in ["DRIVE", "ARM"]:
        rover_data["mode"] = mode
    return jsonify({"status": "ok"})

@app.route('/')
def index(): return render_template('manual.html')

@app.route('/api/telemetry')
def get_telemetry(): return jsonify(rover_data)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
