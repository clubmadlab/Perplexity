#############################################################################
# FILE:      piezo.py														#
# CONTENTS:  Piezo speaker module											#
# COPYRIGHT: MadLab Ltd. 2026												#
# AUTHOR:    James Hutchby  												#
# UPDATED:   06/04/26   													#
#############################################################################

from machine import Pin, PWM
from rp2 import PIO, StateMachine, asm_pio
from time import sleep

from button import *
from solved import solved


#------------------------------------------------------------------------
# notes
#------------------------------------------------------------------------

# sample by grunz -- https://freesound.org/s/109662/ -- License: Attribution 3.0


#------------------------------------------------------------------------
# port assignments (GPIO numbers)
#------------------------------------------------------------------------

PIEZO1_PIN = const(12)
PIEZO2_PIN = const(13)


#------------------------------------------------------------------------
# constants
#------------------------------------------------------------------------

# state machine
PIEZO_SM = const(4)

BEEP_FREQ = const(4000)
BEEP_DURATION = const(150)
SHORT_DURATION = const(20)

CLICK_FREQ = const(4000)
CLICK_DURATION = const(4)

SAMPLE_RATE = const(11_025)
PWM_STEPS = const(256)

# sound effects
SFX_SOLVED = const(1)


#------------------------------------------------------------------------
# PIO
#------------------------------------------------------------------------

@asm_pio()
def _piezo_timer():

    # generate interrupts at SAMPLE_RATE
    label('loop')
    irq(rel(0))
    nop()
    jmp("loop")


#------------------------------------------------------------------------
# initialisation
#------------------------------------------------------------------------

pwm1 = None
pwm2 = None

sample = None
sample_offset = 0

sm = StateMachine(PIEZO_SM, _piezo_timer, freq=SAMPLE_RATE*3)


#------------------------------------------------------------------------
# functions
#------------------------------------------------------------------------

def beep():
    """Plays a beep."""

    global pwm1, pwm2

    pwm1 = PWM(Pin(PIEZO1_PIN))
    pwm2 = PWM(Pin(PIEZO2_PIN), invert=True)

    pwm1.freq(BEEP_FREQ)
    pwm2.freq(BEEP_FREQ)
    pwm1.duty_u16(0x8000)
    pwm2.duty_u16(0x8000)

    sleep(BEEP_DURATION / float(1000))

    pwm1.deinit()
    pwm2.deinit()

    # silence piezo
    Pin(PIEZO1_PIN, Pin.OUT, value=0)
    Pin(PIEZO2_PIN, Pin.OUT, value=0)


def short_beep():
    """Plays a short beep."""

    global pwm1, pwm2

    pwm1 = PWM(Pin(PIEZO1_PIN))
    pwm2 = PWM(Pin(PIEZO2_PIN), invert=True)

    pwm1.freq(BEEP_FREQ)
    pwm2.freq(BEEP_FREQ)
    pwm1.duty_u16(0x8000)
    pwm2.duty_u16(0x8000)

    sleep(SHORT_DURATION / float(1000))

    pwm1.deinit()
    pwm2.deinit()

    # silence piezo
    Pin(PIEZO1_PIN, Pin.OUT, value=0)
    Pin(PIEZO2_PIN, Pin.OUT, value=0)


def click():
    """Plays a click."""

    global pwm1, pwm2

    pwm1 = PWM(Pin(PIEZO1_PIN))
    pwm2 = PWM(Pin(PIEZO2_PIN), invert=True)

    pwm1.freq(CLICK_FREQ)
    pwm2.freq(CLICK_FREQ)
    pwm1.duty_u16(0x8000)
    pwm2.duty_u16(0x8000)

    sleep(CLICK_DURATION / float(1000))

    pwm1.deinit()
    pwm2.deinit()

    # silence piezo
    Pin(PIEZO1_PIN, Pin.OUT, value=0)
    Pin(PIEZO2_PIN, Pin.OUT, value=0)


# interrupt service routine
@micropython.native
def _piezo_isr(timer):

    global pwm1, pwm2, sample, sample_offset

    if sample == None: return

    s = sample[sample_offset]<<8
    pwm1.duty_u16(s)
    pwm2.duty_u16(s)

    sample_offset += 1
    if sample_offset >= len(sample): sample = None

sm.irq(_piezo_isr)


def play_sfx(sfx):
    """Plays a sound effect - fed with the sample index."""

    global pwm1, pwm2, sample, sample_offset

    if sfx == SFX_SOLVED: sample = solved

    sample_offset = 0

    pwm1 = PWM(Pin(PIEZO1_PIN))
    pwm2 = PWM(Pin(PIEZO2_PIN), invert=True)

    # maximum PWM frequency
    pwm1.freq(125_000_000 // PWM_STEPS)
    pwm2.freq(125_000_000 // PWM_STEPS)
    pwm1.duty_u16(0x8000)
    pwm2.duty_u16(0x8000)

    sm.active(1)

    while sample != None:
        if test_button_down():
            sample = None
            break

    sm.active(0)

    pwm1.duty_u16(0x8000)
    pwm2.duty_u16(0x8000)


#------------------------------------------------------------------------
# module test
#------------------------------------------------------------------------

# beep()
# sleep(0.25)
# beep()
# sleep(0.25)
#  
# click()
# sleep(0.25)
# click()
# sleep(0.25)
#  
# while True:
#     play_sfx(SFX_SOLVED)
#     sleep(1.0)
