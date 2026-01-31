#include <AccelStepper.h>
#define EN_PIN 4
#define STEP_PIN 6
#define DIR_PIN 5
#define LIMIT_PIN1 8
#define LIMIT_PIN2 9

AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);
String inputString = "";      // a String to hold incoming data
bool stringComplete = false;  // whether the string is complete
double actual_pos_mm = 0.0;
float radius_mm = 20;
int check_home = 0;

float pulse_to_mm = radius_mm * 0.18 * M_PI / 180.0;

/*
  SerialEvent occurs whenever a new data comes in the hardware serial RX. This
  routine is run between each time loop() runs, so using delay inside loop can
  delay response. Multiple bytes of data may be available.
*/
void serialEvent() {
  while (Serial.available()) {
    // get the new byte:
    char inChar = (char)Serial.read();
    // add it to the inputString:
    inputString += inChar;
    // if the incoming character is a newline, set a flag so the main loop can
    // do something about it:
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}

// MOVE TO STEP POSITION

void moveto_step(long step_pos) {
  stepper.setSpeed(256);
  stepper.moveTo(step_pos);
  while (stepper.distanceToGo() != 0) {
    stepper.run();
  }
  //Serial.println("");
  //Serial.print("On position (mm): ");
  actual_pos_mm = stepper.currentPosition() * pulse_to_mm;
  //Serial.println(actual_pos_mm);
}

void move_relative_step(long step_pos) {
  stepper.setSpeed(256);
  stepper.move(step_pos);
  while (stepper.distanceToGo() != 0) {
    stepper.run();
  }
  //Serial.println("On position");
}


// MOVE TO MM POSITION

void moveto_mm(long step_mm) {
  stepper.setSpeed(256);
  step_mm = step_mm/pulse_to_mm;
  stepper.moveTo(step_mm);
  while (stepper.distanceToGo() != 0) {
    stepper.run();
  }
  actual_pos_mm = stepper.currentPosition() * pulse_to_mm;
  //Serial.println("");
  //Serial.print("On position (mm): ");
  //Serial.println(actual_pos_mm);
}

void disable_stepper() {
  stepper.disableOutputs();
  //Serial.println("Disabled stepper");
}

void enable_stepper() {
  stepper.enableOutputs();
  //Serial.println("Enabled stepper");
}


// ---------- HOMING FUNCTION ----------
void homeStepper() {
  //Serial.println("Starting homing sequence...");
  stepper.setSpeed(-256);
  check_home=0;
  while (check_home < 200) {
    stepper.runSpeed();
    if (digitalRead(LIMIT_PIN1) == LOW){
      check_home++;
    }
  }
  check_home = 0;
  stepper.setCurrentPosition(0);
}
// -------------------------------------

void setup() {
  // initialize serial:
  Serial.begin(9600);
  // reserve 200 bytes for the inputString:
  inputString.reserve(200);
  pinMode(LIMIT_PIN1, INPUT_PULLUP);  // Active LOW
  pinMode(LIMIT_PIN2, INPUT_PULLUP);  // Active LOW
  stepper.setEnablePin(EN_PIN);
  stepper.setMaxSpeed(800);
  stepper.setAcceleration(800);
  stepper.setCurrentPosition(0);
}

void loop() {
  // print the string when a newline arrives:
  if (stringComplete) {
    //call homing
    if (inputString.substring(0, 6) == "Homing") {
      homeStepper();
    }
    if (inputString.substring(0, 11) == "Moveto_step") {
      long t_step = inputString.substring(11, 18).toInt();
      Serial.println(t_step);
      moveto_step(t_step);
      Serial.println(stepper.currentPosition());
    }
    if (inputString.substring(0, 9) == "Moveto_mm") {
      long t_mm = inputString.substring(9, 18).toInt();
      Serial.println(t_mm);
      moveto_mm(t_mm);
      Serial.println(stepper.currentPosition());
    }
    if (inputString.substring(0, 15) == "Disable_Stepper") {
      disable_stepper();
    }
    if (inputString.substring(0, 14) == "Enable_Stepper") {
      enable_stepper();
    }

    // clear the string:
    inputString = "";
    stringComplete = false;
  }
}