#############################################################################
# FILE:      button.py														#
# CONTENTS:  Pushbutton module												#
# COPYRIGHT: MadLab Ltd. 2026												#
# AUTHOR:    James Hutchby  												#
# UPDATED:   03/04/26   													#
#############################################################################

from machine import Pin, Timer
from time import sleep


#------------------------------------------------------------------------
# port assignments (GPIO numbers)
#------------------------------------------------------------------------

BUTTON1_PIN = const(0)
BUTTON2_PIN = const(18)
BUTTON3_PIN = const(11)


#------------------------------------------------------------------------
# constants
#------------------------------------------------------------------------

# number of pushbuttons
NUM_BUTTONS = const(3)


#------------------------------------------------------------------------
# initialisation
#------------------------------------------------------------------------

button1 = Pin(BUTTON1_PIN, Pin.IN, Pin.PULL_UP)
button2 = Pin(BUTTON2_PIN, Pin.IN, Pin.PULL_UP)
button3 = Pin(BUTTON3_PIN, Pin.IN, Pin.PULL_UP)

button_state = [False, False, False]
is_pressed = [False, False, False]
wait_release = [False, False, False]


#------------------------------------------------------------------------
# functions
#------------------------------------------------------------------------

# interrupt service routine
@micropython.native
def _button_isr(timer):

    global button1, button2, button3, button_state, is_pressed, wait_release

    button_state[0] = button1.value() == 0
    button_state[1] = button2.value() == 0
    button_state[2] = button3.value() == 0

    if wait_release[0]:
        if not button_state[0]: wait_release[0] = False
        is_pressed[0] = False
    else:
        is_pressed[0] = button_state[0]

    if wait_release[1]:
        if not button_state[1]: wait_release[1] = False
        is_pressed[1] = False
    else:
        is_pressed[1] = button_state[1]

    if wait_release[2]:
        if not button_state[2]: wait_release[2] = False
        is_pressed[2] = False
    else:
        is_pressed[2] = button_state[2]

button_timer = Timer(period=50, mode=Timer.PERIODIC, callback=_button_isr, hard=True)


@micropython.native
def test_button_pressed(n = None):
    """Returns True if a pushbutton is pressed with debounce - fed with the button index (1 to 3) or null for any button."""

    global is_pressed, wait_release

    if n == None:
        return test_button_pressed(1) or test_button_pressed(2) or test_button_pressed(3)
    elif n == 1:
        if is_pressed[0]: wait_release[0] = True
        return is_pressed[0]
    elif n == 2:
        if is_pressed[1]: wait_release[1] = True
        return is_pressed[1]
    elif n == 3:
        if is_pressed[2]: wait_release[2] = True
        return is_pressed[2]
    else:
        raise Exception("Argument must be 1 to 3 or null")


@micropython.native
def test_button_down(n = None):
    """Returns True if a pushbutton is currently down - fed with the button index (1 to 3) or null for any button."""

    if n == None: return button_state[0] or button_state[1] or button_state[2]
    elif n == 1: return button_state[0]
    elif n == 2: return button_state[1]
    elif n == 3: return button_state[2]
    else: raise Exception("Argument must be 1 to 3 or null")


@micropython.native
def test_break():
    """Returns True if any two or more pushbuttons currently down."""

    down = 0
    if test_button_down(1): down += 1
    if test_button_down(2): down += 1
    if test_button_down(3): down += 1
    return down >= 2


#------------------------------------------------------------------------
# module test
#------------------------------------------------------------------------

# while True:
#     if test_button_down(): print("button down")
#     if test_button_down(1): print("#1 down")
#     if test_button_down(2): print("#2 down")
#     if test_button_down(3): print("#3 down")
#     if test_button_pressed(1): print("#1 pressed")
#     if test_button_pressed(2): print("#2 pressed")
#     if test_button_pressed(3): print("#3 pressed")
#     sleep(0.1)
