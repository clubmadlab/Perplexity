#############################################################################
# FILE:      touch.py														#
# CONTENTS:  Touch switch module											#
# COPYRIGHT: MadLab Ltd. 2026												#
# AUTHOR:    James Hutchby  												#
# UPDATED:   03/04/26   													#
#############################################################################

# dynamic threshold ?
# wait release ?

from machine import Pin
from rp2 import PIO, StateMachine, asm_pio
from time import sleep


#------------------------------------------------------------------------
# port assignments (GPIO numbers)
#------------------------------------------------------------------------

TOUCH1_PIN = const(1)
TOUCH2_PIN = const(17)
TOUCH3_PIN = const(15)


#------------------------------------------------------------------------
# constants
#------------------------------------------------------------------------

# state machines
TOUCH_SM1 = const(4)
TOUCH_SM2 = const(5)
TOUCH_SM3 = const(6)

FREQ = const(125_000_000)

TOUCH_THRESHOLD = const(60)


#------------------------------------------------------------------------
# PIO
#------------------------------------------------------------------------

@asm_pio(set_init=PIO.OUT_HIGH, autopush=False)
def _get_touch_pulse():

    set(pindirs, 0)
    set(x, 0)
    label('lbl1')
    jmp(x_dec, 'lbl2')
    label('lbl2')
    nop()
    jmp(pin, 'lbl1')
    mov(isr, x)
    push()


#------------------------------------------------------------------------
# initialisation
#------------------------------------------------------------------------

touch1 = Pin(TOUCH1_PIN, Pin.OUT, Pin.PULL_DOWN)
touch2 = Pin(TOUCH2_PIN, Pin.OUT, Pin.PULL_DOWN)
touch3 = Pin(TOUCH3_PIN, Pin.OUT, Pin.PULL_DOWN)

touch1.on()
touch2.on()
touch3.on()


#------------------------------------------------------------------------
# functions
#------------------------------------------------------------------------

@micropython.native
def get_touch_raw(n):
    """Gets the raw value from a touch switch - fed with the touch switch index (1 to 3)."""

    global touch1, touch2, touch3
    global sm1, sm2, sm3

    if n == 1:
        sm1 = StateMachine(TOUCH_SM1, _get_touch_pulse, in_base=touch1, jmp_pin=touch1, set_base=touch1, freq=FREQ)
        sm1.active(1)
        return 0xffff_ffff - sm1.get()
    elif n == 2:
        sm2 = StateMachine(TOUCH_SM2, _get_touch_pulse, in_base=touch2, jmp_pin=touch2, set_base=touch2, freq=FREQ)
        sm2.active(1)
        return 0xffff_ffff - sm2.get()
    elif n == 3:
        sm3 = StateMachine(TOUCH_SM3, _get_touch_pulse, in_base=touch3, jmp_pin=touch3, set_base=touch3, freq=FREQ)
        sm3.active(1)
        return 0xffff_ffff - sm3.get()
    else: raise Exception("Argument must be 1 to 3")


@micropython.native
def test_touch_pressed(n = None):
    """Returns True if a touch switch is pressed - fed with the touch switch index (1 to 3) or null for any touch switch."""

    if n == None: return get_touch_raw(1) > TOUCH_THRESHOLD or get_touch_raw(2) > TOUCH_THRESHOLD or get_touch_raw(3) > TOUCH_THRESHOLD
    elif n == 1: return get_touch_raw(1) > TOUCH_THRESHOLD
    elif n == 2: return get_touch_raw(2) > TOUCH_THRESHOLD
    elif n == 3: return get_touch_raw(3) > TOUCH_THRESHOLD
    else: raise Exception("Argument must be 1 to 3 or null")


#------------------------------------------------------------------------
# module test
#------------------------------------------------------------------------

# while True:
#     print(get_touch_raw(1), get_touch_raw(2), get_touch_raw(3))
#     if test_touch_pressed(1): print("#1 pressed")
#     if test_touch_pressed(2): print("#2 pressed")
#     if test_touch_pressed(3): print("#3 pressed")
#     sleep(0.25)
