#include <Servo.h>

Servo servo1;
Servo servo2;
Servo servo3;
Servo servo4;

// Create a buffer to hold the incoming radio string
const int BUFFER_SIZE = 32;
char buf[BUFFER_SIZE];
int bufIndex = 0;

void setup() {
  // Match the Jetson's baud rate exactly
  Serial.begin(9600);
  
  // Attach the pins exactly as they are physically wired
  servo1.attach(3);
  servo2.attach(5);
  servo3.attach(6);
  servo4.attach(11); 

  // Initialize all servos to dead center upon boot
  servo1.writeMicroseconds(1500);
  servo2.writeMicroseconds(1500);
  servo3.writeMicroseconds(1500);
  servo4.writeMicroseconds(1500);
}

void loop() {
  // Rapidly scoop up incoming data without freezing the processor
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n') {
      // The message is complete! Null-terminate the string and parse it.
      buf[bufIndex] = '\0'; 
      parseCommand(buf);
      bufIndex = 0; // Reset the buffer for the next message
    } else {
      // Prevent buffer overflows just in case of radio noise
      if (bufIndex < BUFFER_SIZE - 1) {
        buf[bufIndex++] = c;
      }
    }
  }
}

void parseCommand(char* command) {
  // 1. Search the string for the start bracket '<'
  // It will naturally ignore the 'O', 'R', 'G', or 'B' LED command at the front!
  char* start = strchr(command, '<');
  
  if (start != NULL) {
    int s1, s2, s3, s4;
    
    // 2. Extract exactly 4 integers formatted as <#,#,#,#>
    if (sscanf(start, "<%d,%d,%d,%d>", &s1, &s2, &s3, &s4) == 4) {
      
      // 3. Hardware Failsafe: Only send the command if it is physically safe
      if (s1 >= 500 && s1 <= 2500) servo1.writeMicroseconds(s1);
      if (s2 >= 500 && s2 <= 2500) servo2.writeMicroseconds(s2);
      if (s3 >= 500 && s3 <= 2500) servo3.writeMicroseconds(s3);
      if (s4 >= 500 && s4 <= 2500) servo4.writeMicroseconds(s4);
      
    }
  }
}