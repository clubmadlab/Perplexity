#############################################################################
# FILE:      led.py															#
# CONTENTS:  LED module														#
# COPYRIGHT: MadLab Ltd. 2026												#
# AUTHOR:    James Hutchby  												#
# UPDATED:   18/10/26   													#
#############################################################################

from machine import Pin
from rp2 import PIO, StateMachine, asm_pio, DMA
from time import sleep, sleep_us

from button import test_break


#------------------------------------------------------------------------
# port assignments (GPIO numbers)
#------------------------------------------------------------------------

LEDS_PIN = const(6)


#------------------------------------------------------------------------
# constants
#------------------------------------------------------------------------

# number of LEDs
NUM_LEDS = const(6)

# state machine
LEDS_SM = const(3)

# 50ns
LEDS_FREQ = const(20_000_000)

# LEDs reset time in us
LEDS_RESET = const(300)

# hues
HUE_RED = const(0)
HUE_YELLOW = const(60)
HUE_GREEN = const(120)
HUE_CYAN = const(180)
HUE_BLUE = const(240)
HUE_MAGENTA = const(300)
NUM_HUES = const(360)

# standard colours
LCD_BLACK = const(0x0000_0000)
LCD_RED = const(0xf800_f800)
LCD_GREEN = const(0x07e0_07e0)
LCD_BLUE = const(0x001f_0001f)
LCD_CYAN = const(0x07ff_07ff)
LCD_MAGENTA = const(0xf81f_f81f)
LCD_YELLOW = const(0xffe0_ffe0)
LCD_WHITE = const(0xffff_ffff)
LCD_ORANGE = const(0xfb00_fb00)
LCD_PINK = const(0xfa35_fa35)

# defaults
DEFAULT_RGB_COMPONENT = const(0x20)
DEFAULT_SATURATION = const(1.0)
DEFAULT_VALUE = const(0.125)

fade_steps = [0, 0x01, 0x02, 0x03, 0x04, 0x06, 0x08, 0x0b, 0x10, 0x16, 0x20]

# colour states
class Colour:
    Black = const(0)
    Red = const(1)
    Green = const(2)
    Blue = const(3)
    Cyan = const(4)
    Magenta = const(5)
    Yellow = const(6)
    White = const(7)
    Orange = const(8)
    Pink = const(9)

    @staticmethod
    def to_rgb(colour):
        """to RGB components tuple"""
        if colour == Colour.Black: return (0, 0, 0)
        elif colour == Colour.Red: return (DEFAULT_RGB_COMPONENT, 0, 0)
        elif colour == Colour.Green: return (0, DEFAULT_RGB_COMPONENT, 0)
        elif colour == Colour.Blue: return (0, 0, DEFAULT_RGB_COMPONENT)
        elif colour == Colour.Cyan: return (0, DEFAULT_RGB_COMPONENT, DEFAULT_RGB_COMPONENT)
        elif colour == Colour.Magenta: return (DEFAULT_RGB_COMPONENT, 0, DEFAULT_RGB_COMPONENT)
        elif colour == Colour.Yellow: return (DEFAULT_RGB_COMPONENT, DEFAULT_RGB_COMPONENT, 0)
        elif colour == Colour.White: return (DEFAULT_RGB_COMPONENT, DEFAULT_RGB_COMPONENT, DEFAULT_RGB_COMPONENT)
        elif colour == Colour.Orange: return (DEFAULT_RGB_COMPONENT, DEFAULT_RGB_COMPONENT//2, 0)
        elif colour == Colour.Pink: return (31, 8, 21)
        else: return (0, 0, 0)

    @staticmethod
    def to_lcd(colour):
        """to packed LCD word"""
        if colour == Colour.Black: return LCD_BLACK
        elif colour == Colour.Red: return LCD_RED
        elif colour == Colour.Green: return LCD_GREEN
        elif colour == Colour.Blue: return LCD_BLUE
        elif colour == Colour.Cyan: return LCD_CYAN
        elif colour == Colour.Magenta: return LCD_MAGENTA
        elif colour == Colour.Yellow: return LCD_YELLOW
        elif colour == Colour.White: return LCD_WHITE
        elif colour == Colour.Orange: return LCD_ORANGE
        elif colour == Colour.Pink: return LCD_PINK
        else: return 0

    @staticmethod
    def to_string(colour):
        if colour == Colour.Black: return " "
        elif colour == Colour.Red: return "R"
        elif colour == Colour.Green: return "G"
        elif colour == Colour.Blue: return "B"
        elif colour == Colour.Cyan: return "C"
        elif colour == Colour.Magenta: return "M"
        elif colour == Colour.Yellow: return "Y"
        elif colour == Colour.White: return "W"
        elif colour == Colour.Orange: return "O"
        elif colour == Colour.Pink: return "P"
        else: return " "


#------------------------------------------------------------------------
# PIO
#------------------------------------------------------------------------

@asm_pio(set_init=PIO.OUT_LOW, sideset_init=PIO.OUT_LOW, side_pindir=True, out_shiftdir=PIO.SHIFT_LEFT,
  autopull=True, pull_thresh=24, fifo_join=PIO.JOIN_TX)
def _tx_leds():

    # WS2812B timings in ns
    TRES = const(75000)
    T0H = const(400)
    T0L = const(850)
    T1H = const(800)
    T1L = const(450)

    T1 = int(T0H / 50)
    T2 = int((T1H - T0H) / 50)
    T3 = int(T1L / 50)

    set(pins, 0).side(1)							# driven low, or tristated and pulled high
    label('bitloop')
    out(x, 1).side(1).delay(T3-1)					# data pin low
    jmp(not_x, 'do_zero').side(0).delay(T1-1)		# data pin high
    label('do_one')
    jmp('bitloop').side(0).delay(T2-1)
    label('do_zero')
    jmp('bitloop').side(1).delay(T2-1)


#------------------------------------------------------------------------
# initialisation
#------------------------------------------------------------------------

leds = Pin(LEDS_PIN, Pin.OUT, value=0)

sm = StateMachine(LEDS_SM, _tx_leds, freq=LEDS_FREQ, set_base=leds, sideset_base=leds)
sm.active(1)

# GRB << 8, little endian
colours = bytearray(NUM_LEDS*4)
_colours = bytearray(NUM_LEDS*4)

dma = DMA()


#------------------------------------------------------------------------
# functions
#------------------------------------------------------------------------

@micropython.native
def update_all_leds():
    """Updates all LEDs."""

    global sm, colours, dma

    # reset
    sm.exec("set(pins, 0).side(1)")
    sleep_us(LEDS_RESET)

    DREQ_PIO0_TX0 = const(0)
    ctrl = dma.pack_ctrl(high_pri=True, size=2, inc_read=True, inc_write=False, treq_sel=DREQ_PIO0_TX0+LEDS_SM)
    dma.config(read=colours, write=sm, count=NUM_LEDS, ctrl=ctrl, trigger=True)

    while dma.active(): pass
    while sm.tx_fifo() != 0: pass
    sleep_us(100)


@micropython.native
def reset_led(n, update = True):
    """Resets an LED - fed with the LED index (1 to 6) and an update flag."""

    if n < 1 or n > NUM_LEDS: raise Exception("Argument must be 1 to 6")

    global colours
    colours[(n-1)*4+0] = 0
    colours[(n-1)*4+1] = 0
    colours[(n-1)*4+2] = 0
    colours[(n-1)*4+3] = 0
    if update: update_all_leds()


@micropython.native
def reset_all_leds(update = True):
    """Resets all LEDs to black - fed with an update flag."""

    for n in range(NUM_LEDS): reset_led(n+1, False)
    if update: update_all_leds()


@micropython.native
def set_led_rgb(n, red, green, blue, update = True):
    """Sets an LED to a colour - fed with the LED index (1 to 6), the RGB components and an update flag."""

    if n < 1 or n > NUM_LEDS: raise Exception("LED index must be 1 to 6")

    global colours
    colours[(n-1)*4+0] = 0
    colours[(n-1)*4+1] = blue
    colours[(n-1)*4+2] = red
    colours[(n-1)*4+3] = green
    if update: update_all_leds()


@micropython.native
def set_all_leds_rgb(red, green, blue, update = True):
    """Sets all LEDs to a colour - fed with the RGB components and an update flag."""

    for n in range(NUM_LEDS): set_led_rgb(n+1, red, green, blue, False)
    if update: update_all_leds()


@micropython.native
def set_led_hsv(n, hue, saturation = DEFAULT_SATURATION, value = DEFAULT_VALUE, update = True):
    """Sets an LED to a colour - fed with the LED index (1 to 6), the HSV components and an update flag."""

    if n < 1 or n > NUM_LEDS: raise Exception("LED index must be 1 to 6")

    h = (hue//60) % 6
    f = hue/60.0 - hue//60

    v = int(value * 255)
    p = int(value * 255 * (1.0 - saturation))
    q = int(value * 255 * (1.0 - f * saturation))
    r = int(value * 255 * (1.0 - (1.0 - f) * saturation))

    if h == 0: set_led_rgb(n, v, r, p, update)
    elif h == 1: set_led_rgb(n, q, v, p, update)
    elif h == 2: set_led_rgb(n, p, v, r, update)
    elif h == 3: set_led_rgb(n, p, q, v, update)
    elif h == 4: set_led_rgb(n, r, p, v, update)
    else: set_led_rgb(n, v, p, q, update)


@micropython.native
def set_all_leds_hsv(hue, saturation = DEFAULT_SATURATION, value = DEFAULT_VALUE, update = True):
    """Sets all LEDs to a colour - fed with the HSV components and an update flag."""

    for n in range(NUM_LEDS): set_led_hsv(n+1, hue, saturation, value, False)
    if update: update_all_leds()


def fade_out_led(n, wait = 0.01):
    """Fades out an LED - fed with the LED index (1 to 6)."""

    global colours, fade_steps

    if n < 1 or n > NUM_LEDS: raise Exception("LED index must be 1 to 6")

    i = (n-1)*4

    step = len(fade_steps)-1
    while True:
        if colours[i+1] != 0: colours[i+1] = fade_steps[step]
        if colours[i+2] != 0: colours[i+2] = fade_steps[step]
        if colours[i+3] != 0: colours[i+3] = fade_steps[step]
        update_all_leds()
        if test_break(): return
        sleep(wait)
        if colours[i+1] == 0 and colours[i+2] == 0 and colours[i+3] == 0: break;
        step -= 1


def fade_out_masked_leds(mask = -1, wait = 0.01):
    """Fades out masked LEDs."""

    global colours, fade_steps

    step = len(fade_steps)-1
    while True:
        finished = True
        for n in range(NUM_LEDS):
            if mask & (1<<n) == 0: continue
            i = n*4
            if colours[i+1] != 0: colours[i+1] = fade_steps[step]
            if colours[i+2] != 0: colours[i+2] = fade_steps[step]
            if colours[i+3] != 0: colours[i+3] = fade_steps[step]
            if colours[i+1] != 0 or colours[i+2] != 0 or colours[i+3] != 0: finished = False
        update_all_leds()
        if test_break(): return
        sleep(wait)
        if finished: break
        step -= 1


def fade_in_led(n, wait = 0.01):
    """Fades in an LED - fed with the LED index (1 to 6)."""

    global colours, fade_steps

    if n < 1 or n > NUM_LEDS: raise Exception("LED index must be 1 to 6")

    _colours[:] = colours[:]

    i = (n-1)*4
    colours[i+1] = 0
    colours[i+2] = 0
    colours[i+3] = 0

    step = 0
    while True:
        if colours[i+1] < _colours[i+1]: colours[i+1] = fade_steps[step]
        if colours[i+2] < _colours[i+2]: colours[i+2] = fade_steps[step]
        if colours[i+3] < _colours[i+3]: colours[i+3] = fade_steps[step]
        update_all_leds()
        if test_break(): return
        sleep(wait)
        if colours[i+1] == _colours[i+1] and colours[i+2] == _colours[i+2] and colours[i+3] == _colours[i+3]: break;
        step += 1


def fade_in_masked_leds(mask = -1, wait = 0.01):
    """Fades in masked LEDs."""

    global colours, fade_steps

    _colours[:] = colours[:]

    for n in range(NUM_LEDS):
        if mask & (1<<n) == 0: continue
        i = n*4
        colours[i+1] = 0
        colours[i+2] = 0
        colours[i+3] = 0

    step = 0
    while True:
        finished = True
        for n in range(NUM_LEDS):
            if mask & (1<<n) == 0: continue
            i = n*4
            if colours[i+1] < _colours[i+1]: colours[i+1] = fade_steps[step]
            if colours[i+2] < _colours[i+2]: colours[i+2] = fade_steps[step]
            if colours[i+3] < _colours[i+3]: colours[i+3] = fade_steps[step]
            if colours[i+1] < _colours[i+1] or colours[i+2] < _colours[i+2] or colours[i+3] < _colours[i+3]: finished = False
        update_all_leds()
        if test_break(): return
        sleep(wait)
        if finished: break
        step += 1


#------------------------------------------------------------------------
# module test
#------------------------------------------------------------------------

# test all LEDs
set_all_leds_rgb(DEFAULT_RGB_COMPONENT, 0, 0, True)
sleep(0.5)
set_all_leds_rgb(0, DEFAULT_RGB_COMPONENT, 0, True)
sleep(0.5)
set_all_leds_rgb(0, 0, DEFAULT_RGB_COMPONENT, True)
sleep(0.5)
reset_all_leds()


# while (True):
# 
#     set_led_rgb(1, 0x40, 0, 0, False)			# red
#     set_led_rgb(2, 0, 0x40, 0, False)			# green
#     set_led_rgb(3, 0, 0, 0x40, False)			# blue
#     set_led_rgb(4, 0x40, 0x40, 0, False)		# yellow
#     set_led_rgb(5, 0x40, 0, 0x40, False)		# magenta
#     set_led_rgb(6, 0, 0x40, 0x40, False)		# cyan
#     update_all_leds()
#     sleep(1)
# 
#     set_all_leds_rgb(0x40, 0, 0, True)			# red
#     sleep(1)
#     set_all_leds_rgb(0, 0x40, 0, True)			# green
#     sleep(1)
#     set_all_leds_rgb(0, 0, 0x40, True)			# blue
#     sleep(1)
#     set_all_leds_rgb(0x40, 0x40, 0, True)		# yellow
#     sleep(1)
#     set_all_leds_rgb(0x40, 0, 0x40, True)		# magenta
#     sleep(1)
#     set_all_leds_rgb(0, 0x40, 0x40, True)		# cyan
#     sleep(1)
# 
#     set_all_leds_hsv(30)						# red/yellow
#     sleep(1)
#     set_all_leds_hsv(90)						# yellow/green
#     sleep(1)
#     set_all_leds_hsv(150)						# green/cyan
#     sleep(1)
#     set_all_leds_hsv(210)						# cyan/blue
#     sleep(1)
#     set_all_leds_hsv(270)						# blue/magenta
#     sleep(1)
#     set_all_leds_hsv(330)						# magenta/red
#     sleep(1)
# 
#     reset_all_leds()
#     sleep(1)
