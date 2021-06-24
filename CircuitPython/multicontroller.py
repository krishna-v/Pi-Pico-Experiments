import board
import rotaryio
import digitalio
import usb_hid
import json
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.mouse import Mouse
from adafruit_hid.consumer_control_code import ConsumerControlCode

class Button(object):
    def __init__(self, name, gpio, pullup=digitalio.Pull.DOWN):
        self.name = name
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
    
    def check(self, callback):
        prev_val = self.curr_val
        new_val = self.value()
        if(prev_val != new_val):
            _event = "release" if new_val == self.start_val else "press"
            print(f"Button {self.name} {_event}")
            if(callback):
                callback(name=self.name, ctrltype=type(self).__name__, func="button", event=_event)

class KeyMatrix(object):
    def __init__(self, name, rows, cols):
        self.name = name
        self.rows = []
        self.cols = []
        self.states = []
        self.numrows = len(rows)
        self.numcols = len(cols)
        
        for i in range(0, self.numrows):
            row = digitalio.DigitalInOut(rows[i])
            row.direction = digitalio.Direction.INPUT
            row.pull = digitalio.Pull.DOWN
            self.rows.append(row)
        for i in range(0, self.numcols):
            col = digitalio.DigitalInOut(cols[i])
            col.direction = digitalio.Direction.INPUT
            col.pull = digitalio.Pull.DOWN
            self.cols.append(col)
        for i in range(0, self.numrows * self.numcols):
            self.states.append(False)
            
    def check(self, callback):
        for r in range(0, self.numrows):
            row = self.rows[r]
            row.direction = digitalio.Direction.OUTPUT
            row.value = True
            for c in range(0, self.numcols):
                col = self.cols[c]
                if col.value != self.states[self.numrows * r + c]:
                    _event = "press" if col.value else "release"
                    print(f"Row {r+1} Col {c+1} {_event}")
                    if(callback):
                        callback(name =self.name, ctrltype=type(self).__name__, func=str(self.numrows * r + c), event=_event)
                    self.states[self.numrows * r + c] = col.value
            row.value = False
            row.direction = digitalio.Direction.INPUT
            row.pull = digitalio.Pull.DOWN

class RotaryKnob(object):
    def __init__(self, name, knob_gpio1, knob_gpio2, btn_gpio, btn_pullup=digitalio.Pull.DOWN):
        self.name = name
        self.knob = rotaryio.IncrementalEncoder(knob_gpio1, knob_gpio2)
        self.knob_offset = self.knob.position
        self.btn = Button(name, btn_gpio, btn_pullup)
        
    def check(self, callback):
        position = self.knob.position
        if position < self.knob_offset:
            print(f"knob {self.name} turned left")
            if(callback):
                callback(name=self.name, ctrltype=type(self).__name__, func="left") 
        elif position > self.knob_offset:
            print(f"knob {self.name} turned right")
            if(callback):
                callback(name=self.name, ctrltype=type(self).__name__, func="right") 
        self.knob_offset = position
        self.btn.check(callback)

ctrlmap = json.loads("{}")
hid_devs = {}

def getdevice(dtype):
    dev = hid_devs.get(dtype)
    if(dev): return dev
    
    if(dtype == "ConsumerControl"): dev = ConsumerControl(usb_hid.devices)
    elif(dtype == "Keyboard"): dev = Keyboard(usb_hid.devices)
    elif(dtype == "Mouse"): dev = Mouse(usb_hid.devices)
    else: print(f"unknown HID Device Type: {dtype}");

    if(dev):
        print(f"Created new device of type {dtype}")
        hid_devs[dtype] = dev
    return dev

def callback(name, ctrltype, func, event=None):
    print(f"Name: {name}, Type: {ctrltype}, Func: {func}, Event: {event}")
    map_id = "1" if mode_switch.is_pressed() else "0"  
    try:
        ctrl_block = ctrlmap[map_id][name][func]       
        event_type = ctrl_block.get("type")
        if(event_type != None and event != event_type): return           
        for action in ctrl_block["actions"]:
            key = action["key"]
            name = action.get("name")
            dev = getdevice(action["device"])
            if(type(key) != list): key = [ key ]
            if(not dev): continue
            # TODO: Need to handle mouse events
            if(not event_type and (ctrltype == "Button" or ctrltype == "KeyMatrix")):
                if(event == "press"): dev.press(*key)
                elif(event == "release"): dev.release(*key)
            else: dev.send(*key)           
            if(name): print(name)
    except KeyError:
        print("Could not find action to perform.")

###############################################################

try:
    f = open("ctrlmap.json", 'r')
    ctrlmap = json.load(f)
    f.close()
except:
    print("Could not load control map. Controls won't do anything.");

mode_switch = Button("shift", board.GP14)
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
led.value = False

devices = []
knob = RotaryKnob("knob1", board.GP2, board.GP3, board.GP6, digitalio.Pull.UP)
devices.append(knob)

rows = [ board.GP22, board.GP26, board.GP27, board.GP28 ]
cols = [ board.GP18, board.GP19, board.GP20, board.GP21 ]
matrix = KeyMatrix("keypad", rows, cols)
devices.append(matrix)

ctrlpad = ConsumerControl(usb_hid.devices)

while True:
    led.value = mode_switch.is_pressed()
    
    for dev in devices:
        dev.check(callback)
        
