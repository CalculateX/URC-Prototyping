import serial
import time
import pygame

# --- CONFIGURATION ---
# Change this to whatever COM port your Arduino Nano shows up as (e.g., 'COM3', 'COM4')
ARDUINO_PORT = 'COM25' 
BAUD_RATE = 115200

# Servo starting positions (90 degrees / neutral)
angles = {
    "turntable": 90.0,
    "pitch": 90.0,
    "roll": 90.0,
    "gripper": 90.0
}

def main():
    print("--- Laptop Servo Tester ---")
    
    # Connect to Arduino
    try:
        arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2) # Wait for Arduino to reset upon connection
        print(f"Connected to Arduino on {ARDUINO_PORT}")
    except Exception as e:
        arduino = None
        print(f"Failed to connect to Arduino: {e}")
        print("Running in console-only mode for testing.")

    # Initialize Pygame and Controller
    pygame.init()
    pygame.joystick.init()
    
    if pygame.joystick.get_count() == 0:
        print("No controller detected! Please plug one in and restart.")
        return
        
    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"Controller detected: {joy.get_name()}")
    
    print("Starting control loop. Press Ctrl+C to stop.")
    
    try:
        while True:
            pygame.event.pump()
            
            # 1. Turntable (Left Stick X-Axis: Axis 0)
            turn_input = joy.get_axis(0)
            if abs(turn_input) > 0.1: # Deadzone
                angles["turntable"] += turn_input * 2.0
                
            # 2. Wrist Pitch (Right Stick Y-Axis: Axis 3)
            # Note: Pygame axes might be inverted. If up goes down, change the + to a -
            pitch_input = joy.get_axis(3)
            if abs(pitch_input) > 0.1: # Deadzone
                angles["pitch"] += pitch_input * 2.0
                
            # 3. Wrist Roll (Bumpers: RB=5, LB=4)
            if joy.get_button(5):
                angles["roll"] += 2.0
            elif joy.get_button(4):
                angles["roll"] -= 2.0
                
            # 4. Gripper (Triggers: RT=Axis 5, LT=Axis 4)
            # Pygame triggers usually go from -1.0 (unpressed) to 1.0 (fully pressed)
            raw_rt = (joy.get_axis(5) + 1) / 2.0
            raw_lt = (joy.get_axis(4) + 1) / 2.0
            
            if raw_rt > 0.5:
                angles["gripper"] = 180.0
            elif raw_lt > 0.5:
                angles["gripper"] = 0.0

            # Clamp all values between 0 and 180 degrees
            for key in angles:
                angles[key] = max(0.0, min(180.0, angles[key]))
                
            # Format and send string
            command_str = f"{angles['turntable']:.1f},{angles['pitch']:.1f},{angles['roll']:.1f},{angles['gripper']:.1f},0.0\n"
            
            if arduino and arduino.is_open:
                arduino.write(command_str.encode('utf-8'))
                
            # Print to console so you can verify the outputs
            print(f"Sending: {command_str.strip()}      ", end='\r')
            
            time.sleep(0.05) # 20Hz update rate
            
    except KeyboardInterrupt:
        print("\nExiting tester...")
    finally:
        if arduino and arduino.is_open:
            arduino.close()
        pygame.quit()

if __name__ == '__main__':
    main()