#############################################################################
# FILE:      rotary.py														#
# CONTENTS:  Rotary encoder module											#
# COPYRIGHT: MadLab Ltd. 2026												#
# AUTHOR:    James Hutchby  												#
# UPDATED:   06/04/26   													#
#############################################################################

from machine import Pin, Timer
from time import sleep


#------------------------------------------------------------------------
# port assignments (GPIO numbers)
#------------------------------------------------------------------------

CHANNEL1A_PIN = const(8)
CHANNEL1B_PIN = const(10)
CHANNEL2A_PIN = const(27)
CHANNEL2B_PIN = const(28)
CHANNEL3A_PIN = const(16)
CHANNEL3B_PIN = const(14)


#------------------------------------------------------------------------
# constants
#------------------------------------------------------------------------

# based on an algorithm by Ben Buxton (bb@cactii.net)

DIR_CW = const(0x10)
DIR_CCW = const(0x20)

# full-step states
FULL_START = const(0x0)
FULL_CW_END = const(0x1)
FULL_CW_BEGIN = const(0x2)
FULL_CW_NEXT = const(0x3)
FULL_CCW_BEGIN = const(0x4)
FULL_CCW_END = const(0x5)
FULL_CCW_NEXT = const(0x6)

# half-step states
HALF_START = const(0x0)
HALF_CCW_BEGIN = const(0x1)
HALF_CW_BEGIN = const(0x2)
HALF_START_M = const(0x3)
HALF_CW_BEGIN_M = const(0x4)
HALF_CCW_BEGIN_M = const(0x5)

# full-step state table
full_step_tbl = bytearray([
    FULL_START, FULL_CW_BEGIN, FULL_CCW_BEGIN, FULL_START,					# FULL_START
    FULL_CW_NEXT, FULL_START, FULL_CW_END, FULL_START | DIR_CW,				# FULL_CW_END
    FULL_CW_NEXT, FULL_CW_BEGIN, FULL_START, FULL_START,					# FULL_CW_BEGIN
    FULL_CW_NEXT, FULL_CW_BEGIN, FULL_CW_END, FULL_START,					# FULL_CW_NEXT
    FULL_CCW_NEXT, FULL_START, FULL_CCW_BEGIN, FULL_START,					# FULL_CCW_BEGIN
    FULL_CCW_NEXT, FULL_CCW_END, FULL_START, FULL_START | DIR_CCW,			# FULL_CCW_END
    FULL_CCW_NEXT, FULL_CCW_END, FULL_CCW_BEGIN, FULL_START					# FULL_CCW_NEXT
])

# half-step state table
half_step_tbl = bytearray([
    HALF_START_M, HALF_CW_BEGIN, HALF_CCW_BEGIN, HALF_START,				# HALF_START
    HALF_START_M | DIR_CCW, HALF_START, HALF_CCW_BEGIN, HALF_START,			# HALF_CCW_BEGIN
    HALF_START_M | DIR_CW, HALF_CW_BEGIN, HALF_START, HALF_START,			# HALF_CW_BEGIN
    HALF_START_M, HALF_CCW_BEGIN_M, HALF_CW_BEGIN_M, HALF_START,			# HALF_START_M
    HALF_START_M, HALF_START_M, HALF_CW_BEGIN_M, HALF_START | DIR_CW,		# HALF_CW_BEGIN_M
    HALF_START_M, HALF_CCW_BEGIN_M, HALF_START_M, HALF_START | DIR_CCW		# HALF_CCW_BEGIN_M
])

DECAY_PERIOD = const(2000)


#------------------------------------------------------------------------
# initialisation
#------------------------------------------------------------------------

# configure pins
channel1A = Pin(CHANNEL1A_PIN, Pin.IN, Pin.PULL_UP)
channel1B = Pin(CHANNEL1B_PIN, Pin.IN, Pin.PULL_UP)
channel2A = Pin(CHANNEL2A_PIN, Pin.IN, Pin.PULL_UP)
channel2B = Pin(CHANNEL2B_PIN, Pin.IN, Pin.PULL_UP)
channel3A = Pin(CHANNEL3A_PIN, Pin.IN, Pin.PULL_UP)
channel3B = Pin(CHANNEL3B_PIN, Pin.IN, Pin.PULL_UP)

state1 = state2 = state3 = 0
position1 = position2 = position3 = 0
offset1 = offset2 = offset3 = 0
decay1 = decay2 = decay3 = 0


#------------------------------------------------------------------------
# functions
#------------------------------------------------------------------------

# interrupt service routine
@micropython.native
def _rotary_isr(timer):

    global DIR_CW, DIR_CCW, full_step_tbl, half_step_tbl

    global channel1A, channel1B, state1, position1, offset1, decay1
    pins = (channel1A.value() << 1) | channel1B.value()
    state1 = full_step_tbl[((state1 & 0xf) << 2) + pins]
    # state1 = half_step_tbl[((state1 & 0xf) << 2) + pins]
    if (state1 & 0x30) == DIR_CW: position1 += 1; decay1 = 0
    elif (state1 & 0x30) == DIR_CCW: position1 -= 1; decay1 = 0
    decay1 += 1
    if decay1 >= DECAY_PERIOD: offset1 = position1; decay1 = 0

    global channel2A, channel2B, state2, position2, offset2, decay2
    pins = (channel2A.value() << 1) | channel2B.value()
    state2 = full_step_tbl[((state2 & 0xf) << 2) + pins]
    # state2 = half_step_tbl[((state2 & 0xf) << 2) + pins]
    if (state2 & 0x30) == DIR_CW: position2 += 1; decay2 = 0
    elif (state2 & 0x30) == DIR_CCW: position2 -= 1; decay2 = 0
    decay2 += 1
    if decay2 >= DECAY_PERIOD: offset2 = position2; decay2 = 0
 
    global channel3A, channel3B, state3, position3, offset3, decay3
    pins = (channel3A.value() << 1) | channel3B.value()
    state3 = full_step_tbl[((state3 & 0xf) << 2) + pins]
    # state3 = half_step_tbl[((state3 & 0xf) << 2) + pins]
    if (state3 & 0x30) == DIR_CW: position3 += 1; decay3 = 0
    elif (state3 & 0x30) == DIR_CCW: position3 -= 1; decay3 = 0
    decay3 += 1
    if decay3 >= DECAY_PERIOD: offset3 = position3; decay3 = 0

rotary_timer = Timer(period=1, mode=Timer.PERIODIC, callback=_rotary_isr, hard=False)


def disable_rotaries():
    """Disables the rotary encoders while samples are playing."""

    rotary_timer.deinit()


def enable_rotaries():
    """Re-enables the rotary encoders."""

    rotary_timer.init(period=1, mode=Timer.PERIODIC, callback=_rotary_isr, hard=False)


@micropython.native
def reset_rotary_position(n):
    """Resets a rotary encoder position to zero - fed with the encoder index (1 to 3)."""

    global position1, position2, position3
    global offset1, offset2, offset3
    global decay1, decay2, decay3
    if n == 1: offset1 = position1
    elif n == 2: offset2 = position2
    elif n == 3: offset3 = position3
    else: raise Exception("Argument must be 1 to 3")


@micropython.native
def get_rotary_position(n):
    """Returns the current position of a rotary encoder - fed with the encoder index (1 to 3)."""

    global position1, position2, position3
    global offset1, offset2, offset3
    if n == 1: return position1 - offset1
    elif n == 2: return position2 - offset2
    elif n == 3: return position3 - offset3
    else: raise Exception("Argument must be 1 to 3")


#------------------------------------------------------------------------
# module test
#------------------------------------------------------------------------

# while (True):
#     sleep(0.5)
#     print(get_rotary_position(1), get_rotary_position(2), get_rotary_position(3))
