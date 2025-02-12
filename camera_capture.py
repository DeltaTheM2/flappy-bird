import RPi.GPIO as GPIO
from picamera2 import Picamera2
from time import sleep
from datetime import datetime

# GPIO setup
BUTTON_PIN = 27
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Camera setup
camera = Picamera2()
camera.configure(camera.create_still_configuration())

print("Ready to capture an image. Press the button!")

try:
    while True:
        # Wait for button press
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            print("Button pressed! Capturing image...")
            
            # Capture image with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"image_{timestamp}.jpg"
            
            camera.start()
            sleep(2)  # Allow the camera to adjust
            camera.capture_file(image_path)
            camera.stop()
            
            print(f"Image saved as {image_path}")
            sleep(1)  # Debounce delay to prevent multiple captures

except KeyboardInterrupt:
    print("Program stopped.")

finally:
    GPIO.cleanup()
