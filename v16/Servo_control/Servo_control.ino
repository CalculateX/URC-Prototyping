#include <Servo.h>

Servo servo1;
Servo servo2;
Servo servo3;
Servo servo4;

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(50); 
  
  servo1.attach(3);
  servo2.attach(5);
  servo3.attach(6);
  servo4.attach(9); 

  servo1.writeMicroseconds(1500);
  servo2.writeMicroseconds(1500);
  servo3.writeMicroseconds(1500);
  servo4.writeMicroseconds(1500);
}

void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    
    // Ignore the 'R/G/B' LED character and wait for the bracket
    if (c == '<') {
      int s1 = Serial.parseInt();
      int s2 = Serial.parseInt();
      int s3 = Serial.parseInt();
      int s4 = Serial.parseInt();

      // SAFETY NET: Only apply the command if it is a valid GoBilda pulse.
      // If the serial line glitches and returns 0, the servo ignores it 
      // and securely holds its current position.
      if (s1 >= 500 && s1 <= 2500) servo1.writeMicroseconds(s1);
      if (s2 >= 500 && s2 <= 2500) servo2.writeMicroseconds(s2);
      if (s3 >= 500 && s3 <= 2500) servo3.writeMicroseconds(s3);
      if (s4 >= 500 && s4 <= 2500) servo4.writeMicroseconds(s4);
    }
  }
}