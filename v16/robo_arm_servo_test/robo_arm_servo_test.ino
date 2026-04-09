#include <Servo.h>

Servo s1, s2, s3, s4, s5, eoat;

String inputLine = "";

// Aux Pins
#define SOLENOID_PIN 2
#define POT_PIN A0
#define BUTTON_PIN 13

int potValue = 0;
int motorSpeed = 0;


void setup() {
  Serial.begin(115200);

  // Servo Pins and Setup
  s1.attach(3);
  // s2.attach(5);
  // s3.attach(6);
  s4.attach(5);
  s5.attach(6);
  eoat.attach(9);

  // Aux Setup
  pinMode(SOLENOID_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
}

void loop() {
  while (Serial.available()) {
    // Read Character of Serial
    char c = Serial.read();

    // Append Character to Message
    if (c == '\n' || c == '\r') {
      if (inputLine.length() > 0) {
        processLine(inputLine);
        inputLine = "";
      }
    } else {
      inputLine += c;
    }

    // Solenoid Control
    if (digitalRead(BUTTON_PIN) == LOW) {
      digitalWrite(SOLENOID_PIN, HIGH);
    } else {
        digitalWrite(SOLENOID_PIN, LOW);
    }

    // Write EOAT Servo From Potentiometer
    potValue = analogRead(POT_PIN);
    motorSpeed = map(potValue, 0, 1023, 0, 255);
    s1.write(motorSpeed);
  }
}

void processLine(String line) {

  Serial.print("RAW: [");
  Serial.print(line);
  Serial.println("]");

  float values[5];
  int index = 0;

  int start = 0;
  int commaIndex;

  while (index < 5) {
    commaIndex = line.indexOf(',', start);

    if (commaIndex == -1 && index < 4) {
      Serial.println("PARSE_FAIL");
      return;
    }

    String token;

    if (commaIndex == -1) {
      token = line.substring(start);
    } else {
      token = line.substring(start, commaIndex);
    }

    values[index] = token.toFloat();
    index++;

    if (commaIndex == -1)
      break;

    start = commaIndex + 1;
  }

  if (index == 5) {
    s1.write(values[0]);
    // s2.write(values[1]);
    // s3.write(values[2]);
    s4.write(values[3]);
    s5.write(values[4]);

    Serial.println("OK");
  } else {
    Serial.println("PARSE_FAIL");
  }
}