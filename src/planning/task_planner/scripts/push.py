import pyrebase
import json
import os
import keyboard  # Import the keyboard library

# Initialize Firebase
firebase_secrets_path = os.path.expanduser("~/firebasesecrets.json")

if not os.path.isfile(firebase_secrets_path):
    raise FileNotFoundError("Firebase secrets file not found")

with open(firebase_secrets_path, 'r') as f:
    config = json.load(f)

firebase = pyrebase.initialize_app(config)

# Specify the Firebase database URL with the scheme
db = firebase.database()

db.remove("")
schema = {
        "button_callback" : False
    }
db.set(schema) # fill
# Define a function to update the 'button_callback' value

def update_button_callback(value):
    try:
        # Update the 'button_callback' value in the database
        db.child("button_callback").set(value)
        print(f"Updated 'button_callback' to {value}")
    except Exception as e:
        print(f"Error updating 'button_callback': {str(e)}")

# Detect key presses and update 'button_callback'
while True:
    key = input("Enter something\n")
    if key == 'c':
        update_button_callback(True)
    elif key == 't':
        update_button_callback(False)
        
