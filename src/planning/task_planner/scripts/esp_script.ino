#include <Arduino.h>
#if defined(ESP32) || defined(ARDUINO_RASPBERRY_PI_PICO_W)
#include <WiFi.h>
#elif defined(ESP8266)
#include <ESP8266WiFi.h>
#elif __has_include(<WiFiNINA.h>)
#include <WiFiNINA.h>
#elif __has_include(<WiFi101.h>)
#include <WiFi101.h>
#elif __has_include(<WiFiS3.h>)
#include <WiFiS3.h>
#endif

int lastButtonState1 = LOW;
int lastButtonState2 = LOW;
unsigned long lastDebounceTime1 = 0;
unsigned long lastDebounceTime2 = 0;
unsigned long debounceDelay = 50; // Adjust this value as needed
int room1 = 0;
int room2 = 0;
int p = 0;
int b = 0;
int t = 0;
int r = 0;
int a = 0;
int s = 0;
int q = 0;
int w = 0;

const int MAX_QUEUE_SIZE = 10;  // Adjust the size as needed
int queue[MAX_QUEUE_SIZE];
int front = 0;
int rear = -1;
int itemCount = 0;



#include <Firebase_ESP_Client.h>

// Provide the token generation process info.
#include <addons/TokenHelper.h>

// Provide the RTDB payload printing info and other helper functions.
#include <addons/RTDBHelper.h>

#define WIFI_SSID "Shaolin's World"
#define WIFI_PASSWORD "sixtimes21"


#define API_KEY "AIzaSyCOGooVhBRo-IXpRi5E96KUFQekYXEGfpg"

#define DATABASE_URL "https://alfred-auxilio-default-rtdb.firebaseio.com/"  //<databaseName>.firebaseio.com or <databaseName>.<region>.firebasedatabase.app

FirebaseData fbdo;

FirebaseAuth auth;
FirebaseConfig config;

unsigned long sendDataPrevMillis = 0;

unsigned long count = 0;

#if defined(ARDUINO_RASPBERRY_PI_PICO_W)
WiFiMulti multi;
#endif

bool isElementInQueue(int element) {
  for (int i = 0; i < itemCount; i++) {
    int index = (front + i) % MAX_QUEUE_SIZE;
    if (queue[index] == element) {
      return true; // Element is already in the queue
    }
  }
  return false; // Element is not in the queue
}

void enqueue(int data) {
if (!isElementInQueue(data)) {    
    rear = (rear + 1) % MAX_QUEUE_SIZE;
    queue[rear] = data;
    itemCount++;
  }
 } 
// int dequeue(int ttt) {
//   if (itemCount > 0) {
//     // int data = queue[front];
//     front = (front + 1) % MAX_QUEUE_SIZE;
//     itemCount--;
//     // return data;
//   } else {
//     // Queue is empty, handle underflow
//     return -1;  // Or use another sentinel value
//   }
// }




void setup() {

  Serial.begin(115200);
  pinMode(D1, INPUT);
  pinMode(D2, INPUT);
  pinMode(D3, INPUT);
  pinMode(D4, INPUT);
#if defined(ARDUINO_RASPBERRY_PI_PICO_W)
  multi.addAP(WIFI_SSID, WIFI_PASSWORD);
  multi.run();
#else
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
#endif

  Serial.print("Connecting to Wi-Fi");
  unsigned long ms = millis();
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(300);
#if defined(ARDUINO_RASPBERRY_PI_PICO_W)
    if (millis() - ms > 10000)
      break;
#endif
  }
  Serial.println();
  Serial.print("Connected with IP: ");
  Serial.println(WiFi.localIP());
  Serial.println();

  Serial.printf("Firebase Client v%s\n\n", FIREBASE_CLIENT_VERSION);

  /* Assign the api key (required) */
  config.api_key = API_KEY;

  /* Assign the user sign in credentials */
  // auth.user.email = USER_EMAIL;
  // auth.user.password = USER_PASSWORD;

  /* Assign the RTDB URL (required) */
  config.database_url = DATABASE_URL;

  /* Assign the callback function for the long running token generation task */
  config.token_status_callback = tokenStatusCallback;  // see addons/TokenHelper.h

  if (Firebase.signUp(&config, &auth, "", "")) {
    Serial.println("ok");
    // signupOK = true;
  } else {
    Serial.printf("%s\n", config.signer.signupError.message.c_str());
  }
  Firebase.reconnectNetwork(true);

  fbdo.setBSSLBufferSize(4096 /* Rx buffer size in bytes from 512 - 16384 */, 1024 /* Tx buffer size in bytes from 512 - 16384 */);

  fbdo.setResponseSize(2048);

  Firebase.begin(&config, &auth);

#if defined(ARDUINO_RASPBERRY_PI_PICO_W)
  config.wifi.clearAP();
  config.wifi.addAP(WIFI_SSID, WIFI_PASSWORD);
#endif

  Firebase.setDoubleDigits(5);

  config.timeout.serverResponse = 10 * 1000;
}



void loop() {
  int buttonState = digitalRead(D1);
  int button2State = digitalRead(D2);
  int button3State = digitalRead(D3);
  int button4State = digitalRead(D4);
  // Serial.println(buttonState);
  // Serial.println(button2State);
  // Serial.println(button3State);
  // Serial.println(button4State);
  // Serial.printf("Get int... %s\n", Firebase.RTDB.getInt(&fbdo, F("/task_complete")) ? String(fbdo.to<int>()).c_str() : fbdo.errorReason().c_str());
  // int myVariable = Firebase.RTDB.getInt(&fbdo, F("/task_complete"));
  // Serial.println(myVariable);
  // if (myVariable>0)
  // {
  //   dequeue(myVariable);
  // }

    // if(buttonState == 0 && p ==0)
    // {
    //   request=1;
    //   b=
    // }



    if (buttonState == 0 && p == 0) {
      Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback"), 1) ? "ok" : fbdo.errorReason().c_str());
      room1 = 0;
      b = 0;
    }

    if (buttonState == 1 && b == 0) {
      // Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback"), 0) ? "ok" : fbdo.errorReason().c_str());

      room1 = 0;
      p = 1;
    }

    if (buttonState == 0 && p == 1) {
      Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback"), 1) ? "ok" : fbdo.errorReason().c_str());

      room1 = 1;
      b = 1;
    }

    if (buttonState == 1 && b == 1) {
      // Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback"), 1) ? "ok" : fbdo.errorReason().c_str());
    
      room1 = 1;
      p = 0;
    }

    if (button2State == 0 && t == 0) {
      Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback2"), 1) ? "ok" : fbdo.errorReason().c_str());
      room2 = 0;
      r = 0;
    }

    if (button2State == 1 && r == 0) {
      // Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback2"), 0) ? "ok" : fbdo.errorReason().c_str());

      room2 = 0;
      t = 1;
    }

    if (button2State == 0 && t == 1) {
      Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback2"), 1) ? "ok" : fbdo.errorReason().c_str());
      room2 = 1;
      r = 1;
    }

    if (button2State == 1 && r == 1) {
      // Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback2"), 1) ? "ok" : fbdo.errorReason().c_str());
      room2 = 1;
      t = 0;
    }

        if (button3State == 0 && s == 0) {
      Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback3"), 1) ? "ok" : fbdo.errorReason().c_str());
      room2 = 0;
      a = 0;
    }

    if (button3State == 1 && a == 0) {
      // Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback3"), 0) ? "ok" : fbdo.errorReason().c_str());

      room2 = 0;
      s = 1;
    }

    if (button3State == 0 && s == 1) {
      Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback3"), 1) ? "ok" : fbdo.errorReason().c_str());
      room2 = 1;
      a = 1;
    }

    if (button3State == 1 && a == 1) {
      // Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback3"), 1) ? "ok" : fbdo.errorReason().c_str());
      room2 = 1;
      s = 0;
    }

        if (button4State == 0 && w == 0) {
      Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback4"), 1) ? "ok" : fbdo.errorReason().c_str());
      room2 = 0;
      q = 0;
    }

    if (button4State == 1 && q == 0) {
      // Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback4"), 0) ? "ok" : fbdo.errorReason().c_str());

      room2 = 0;
      w = 1;
    }

    if (button4State == 0 && w == 1) {
      Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback4"), 1) ? "ok" : fbdo.errorReason().c_str());
      room2 = 1;
      q = 1;
    }

    if (button4State == 1 && q == 1) {
      // Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback4"), 1) ? "ok" : fbdo.errorReason().c_str());
      room2 = 1;
      w = 0;
    }

    // Serial.print("1: ");
    // Serial.println(room1);
    // Serial.print("2: ");
    // Serial.println(room2);
    // Serial.println(buttonState);
    // Serial.println(button2State);

    // Serial.println();

    count++;
  // }
}

// Serial.printf("Set bool... %s\n", Firebase.RTDB.setBool(&fbdo, F("/test/bool"), count % 2 == 0) ? "ok" : fbdo.errorReason().c_str());

// Serial.printf("Get bool... %s\n", Firebase.RTDB.getBool(&fbdo, FPSTR("/test/bool")) ? fbdo.to<bool>() ? "true" : "false" : fbdo.errorReason().c_str());

// bool bVal;
// Serial.printf("Get bool ref... %s\n", Firebase.RTDB.getBool(&fbdo, F("/test/bool"), &bVal) ? bVal ? "true" : "false" : fbdo.errorReason().c_str());

// Serial.printf("Set int... %s\n", Firebase.RTDB.setInt(&fbdo, F("/button_callback"), count) ? "ok" : fbdo.errorReason().c_str());

// Serial.printf("Get int... %s\n", Firebase.RTDB.getInt(&fbdo, F("/button_callback")) ? String(fbdo.to<int>()).c_str() : fbdo.errorReason().c_str());
