import board
import rotaryio
import digitalio
import usb_hid
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

class Button(object):
    def __init__(self, gpio, pullup):
        self.btn = digitalio.DigitalInOut(gpio)
        self.btn.direction = digitalio.Direction.INPUT
        self.btn.pull = pullup
        self.curr_val = self.start_val = self.btn.value
        
    def value(self):
        self.curr_val = self.btn.value
        return self.curr_val
    
    def is_pressed(self):
        return (self.value() != self.start_val)
    
    def was_released(self):
        prev_val = self.curr_val
        new_val = self.value()
        return (prev_val != new_val and new_val == self.start_val)


knob = rotaryio.IncrementalEncoder(board.GP2, board.GP3)
knob_button = Button(board.GP6, digitalio.Pull.UP)
mode_switch = Button(board.GP14, digitalio.Pull.DOWN)

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
led.value = False

ctrlpad = ConsumerControl(usb_hid.devices)

knob_offset = 0

while True:
    track_mode = mode_switch.is_pressed()
    led.value = track_mode
    
    position = knob.position
    if position < knob_offset:
        print("Prev Track" if track_mode else "Volume Down")
        ctrlpad.send(ConsumerControlCode.SCAN_PREVIOUS_TRACK if track_mode else ConsumerControlCode.VOLUME_DECREMENT)
    elif position > knob_offset:
        print("Next Track" if track_mode else "Volume Up")
        ctrlpad.send(ConsumerControlCode.SCAN_NEXT_TRACK if track_mode else ConsumerControlCode.VOLUME_INCREMENT)
    knob_offset = position
    
    if knob_button.was_released():
        print("Play/Pause" if track_mode else "Mute")
        ctrlpad.send(ConsumerControlCode.PLAY_PAUSE if track_mode else ConsumerControlCode.MUTE)
        
