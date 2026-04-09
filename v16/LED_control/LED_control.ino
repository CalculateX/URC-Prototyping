#include <Adafruit_NeoPixel.h>

#define LED_COUNT  1
#define PIN_A      6
#define PIN_B      9
#define BAUD_RATE  9600

Adafruit_NeoPixel stripA(LED_COUNT, PIN_A, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel stripB(LED_COUNT, PIN_B, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(BAUD_RATE);
  
  stripA.begin();
  stripB.begin();
  setBothColors(0, 0, 0);
}

void loop() {
  if (Serial.available() > 0) {
    if (Serial.read() == '<') {
      
      unsigned long start = millis();
      while(Serial.available() == 0) {
        if(millis() - start > 10) return; 
      }
      
      char cmd = Serial.read(); 
      
      switch (cmd) {
        case 'R': setBothColors(255, 0, 0); break;
        case 'G': setBothColors(0, 255, 0); break;
        case 'B': setBothColors(0, 0, 255); break;
        case 'O': setBothColors(0, 0, 0); break;
      }
    }
  }
}

void setBothColors(int g, int r, int b) {
  stripA.setPixelColor(0, stripA.Color(r, g, b));
  stripA.show();
  stripB.setPixelColor(0, stripB.Color(r, g, b));
  stripB.show();
}