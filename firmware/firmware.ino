#include <AccelStepper.h>
#include <ArduinoJson.h>
//Height control
#define EN_H_PIN 6
#define STEP_H_PIN 4
#define DIR_H_PIN 5
#define LIMIT_H_PIN1 30
#define LIMIT_H_PIN2 31
// Rotational control
#define EN_R_PIN 10
#define STEP_R_PIN 8
#define DIR_R_PIN 9

//Enconder Rotational
#define A_PULSE 2
#define B_PULSE 3

//Rotational checkpoints positions
#define CP1 34
#define CP2 35
#define CP3 36
#define CP4 37
#define CP5 38

//BOTONERA
#define HOME 22

//TEMPERATURA CERA
#define TEMP_PIN A0


int index_cp = 0;  //Index for checkpoints

// Create a JSON object
StaticJsonDocument<200> doc;

AccelStepper stepper_H(AccelStepper::DRIVER, STEP_H_PIN, DIR_H_PIN);
AccelStepper stepper_R(AccelStepper::DRIVER, STEP_R_PIN, DIR_R_PIN);


String inputString = "";      // a String to hold incoming data
bool stringComplete = false;  // whether the string is complete
double actual_pos_mm = 0.0;
int actual_index = 0;
double actual_pos_index = 0.0;
float pitch_mm = 20.0;
float microstep = 0.0025;
int check_home = 0;
int step_index = 0;

float pulse_to_mm = pitch_mm * microstep;

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

// MOVE TO MM POSITION

void moveto_mm(long step_mm) {
  stepper_H.setSpeed(1600);
  step_mm = step_mm / pulse_to_mm;
  stepper_H.moveTo(step_mm);
  while (stepper_H.distanceToGo() != 0) {
    stepper_H.run();
  }
  actual_pos_mm = stepper_H.currentPosition() * pulse_to_mm;
  //Serial.println("");
  //Serial.print("On position (mm): ");
  //Serial.println(actual_pos_mm);
}

void disable_stepper_H() {
  stepper_H.disableOutputs();
  //Serial.println("Disabled stepper_H");
}

void enable_stepper_H() {
  stepper_H.enableOutputs();
  //Serial.println("Enabled stepper_H");
}

// ---------- HOMING FUNCTION ----------
void homeStepper_H() {
  //Serial.println("Starting homing sequence...");
  stepper_H.setSpeed(-256);
  check_home = 0;
  while (check_home < 200) {
    stepper_H.runSpeed();
    if (digitalRead(LIMIT_H_PIN1) == LOW) {
      check_home++;
    }
  }
  check_home = 0;
  stepper_H.setCurrentPosition(0);
  actual_pos_mm = stepper_H.currentPosition() * pulse_to_mm;
}
// -------------------------------------

bool check_clearence() {
  // Function to update index_cp based on current position
  bool permit = false;
  // check for reasonable height
  Serial.println("actual pos");
  Serial.println(actual_pos_mm);
  if (actual_pos_mm < 10.0) {
    permit = true;
  } else {
    Serial.println("NO PUEDES ROTAR SIN REALIZAR HOMING");
    homeStepper_H();
    permit = true;
  }
  return permit;
}

void rotateto_index(int index_target) {
  // Function to rotate stepper_R to the target index position
  stepper_R.setSpeed(256);
  step_index = index_target * 400;
  stepper_R.moveTo(step_index);
  while (stepper_R.distanceToGo() != 0) {
    stepper_R.run();
  }
  actual_pos_index = stepper_R.currentPosition() * pulse_to_mm;
}

void setup() {
  // initialize serial:
  Serial.begin(115200);
  // reserve 200 bytes for the inputString:
  inputString.reserve(200);
  pinMode(LIMIT_H_PIN1, INPUT_PULLUP);  // Active LOW
  pinMode(LIMIT_H_PIN2, INPUT_PULLUP);  // Active LOW
  stepper_H.setEnablePin(EN_H_PIN);
  stepper_H.setMaxSpeed(1600);
  stepper_H.setAcceleration(800);
  stepper_H.setCurrentPosition(0);
  stepper_R.setEnablePin(EN_R_PIN);
  stepper_R.setMaxSpeed(800);
  stepper_R.setAcceleration(800);
  stepper_R.setCurrentPosition(0);
}

void loop() {

  // print the string when a newline arrives:
  if (stringComplete) {
    //call homing
    if (inputString.substring(0, 6) == "Homing") {
      homeStepper_H();
    }
    if (inputString.substring(0, 9) == "Moveto_mm") {
      long t_mm = inputString.substring(9, 12).toInt();
      Serial.println(t_mm);
      moveto_mm(t_mm);
      Serial.println(stepper_H.currentPosition());
    }

    if (inputString.substring(0, 7) == "index_n") {
      int index_call = inputString.substring(7, 8).toInt();
      Serial.print("Call for index: ");
      Serial.println(index_call);
      if (actual_index != index_call) {
        if (check_clearence()) {
          rotateto_index(index_call);
          Serial.println(stepper_R.currentPosition());
          actual_index = index_call;
        }
      }
    }


    if (inputString.substring(0, 15) == "Disable_Stepper_H") {
      disable_stepper_H();
    }
    if (inputString.substring(0, 14) == "Enable_Stepper_H") {
      enable_stepper_H();
    }

    // clear the string:
    inputString = "";
    stringComplete = false;
    // Serialize JSON to Serial
    // serializeJson(doc, Serial);
    // Serial.println();
  }
}