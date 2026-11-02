#############################################################################
# FILE:      main.py														#
# CONTENTS:  Perplexity mainline											#
# COPYRIGHT: MadLab Ltd. 2026												#
# AUTHOR:    James Hutchby  												#
# UPDATED:   28/10/26   													#
#############################################################################

from machine import Pin
from time import sleep
from random import seed, randrange
from gc import collect

from piezo import *

# double flash Pico LED and beep twice
led = Pin("LED", Pin.OUT)
led.on()
beep()
led.off()
sleep(0.25)
led.on()
beep()
led.off()

from led import *
from lcd import *
from rotary import *
from button import *
from touch import *


#------------------------------------------------------------------------
# global variables and helper functions
#------------------------------------------------------------------------

NUM_PUZZLES = const(16)

ROTARY_THRESHOLD = const(4)

FADE_WAIT = const(0.01)
LOOP_WAIT = const(0.02)

BLINK_RES = const(20)
BLINK_STEPS = const(1000 // BLINK_RES)

current_puzzle = 1

led_state = []
target_state = []
hues = []

red_flags = green_flags = blue_flags = []

red_ndx = green_ndx = blue_ndx = 0

red_speed = green_speed = blue_speed = 0

red_timer = green_timer = blue_timer = 0

# coords of hexagon vertices
vertex_coords = [(120, 20), (33, 70), (33, 170), (120, 220), (207, 170), (207, 70)]

blink_time = []
time = 0


# draws a PCB hexagon
def draw_hexagon():

    for n in range(6):
        x1, y1 = vertex_coords[n]
        x2, y2 = vertex_coords[(n+1)%6]
        draw_line(x1, y1, x2, y2, LCD_ORANGE)


# draws target colours on the hexagon
def draw_target_colours():

    global target_state

    for n in range(NUM_LEDS):
        x, y = vertex_coords[n]
        colour = target_state[n]
        draw_triple_string(x-12, y-12, Colour.to_string(colour), Colour.to_lcd(colour), LCD_BLACK)


# sets all LED colours
def set_led_colours(update = True):

    global led_state

    for n in range(NUM_LEDS):
        red, green, blue = Colour.to_rgb(led_state[n])
        set_led_rgb(n+1, red, green, blue, False)

    if update: update_all_leds()


# draws instructions
def draw_instructions(y, *strs):

    for str in strs:
        x = (LCD_WIDTH - len(str) * 16) // 2
        draw_double_string(x, y, str, LCD_WHITE, LCD_BLACK)
        y += 20


# maps colour flags to LED states
def flags_to_state():

    global led_state, red_flags, green_flags, blue_flags

    for n in range(NUM_LEDS):
        if red_flags[n] and not green_flags[n] and not blue_flags[n]: led_state[n] = Colour.Red
        elif not red_flags[n] and green_flags[n] and not blue_flags[n]: led_state[n] = Colour.Green
        elif not red_flags[n] and not green_flags[n] and blue_flags[n]: led_state[n] = Colour.Blue
        elif not red_flags[n] and green_flags[n] and blue_flags[n]: led_state[n] = Colour.Cyan
        elif red_flags[n] and not green_flags[n] and blue_flags[n]: led_state[n] = Colour.Magenta
        elif red_flags[n] and green_flags[n] and not blue_flags[n]: led_state[n] = Colour.Yellow
        elif red_flags[n] and green_flags[n] and blue_flags[n]: led_state[n] = Colour.White
        else: led_state[n] = Colour.Black


# maps LED states to colour flags
def state_to_flags():

    global led_state, red_flags, green_flags, blue_flags

    for n in range(NUM_LEDS):
        red_flags[n] = green_flags[n] = blue_flags[n] = False
        if led_state[n] == Colour.Red: red_flags[n] = True
        elif led_state[n] == Colour.Green: green_flags[n] = True
        elif led_state[n] == Colour.Blue: blue_flags[n] = True
        elif led_state[n] == Colour.Cyan: green_flags[n] = blue_flags[n] = True
        elif led_state[n] == Colour.Magenta: red_flags[n] = blue_flags[n] = True
        elif led_state[n] == Colour.Yellow: red_flags[n] = green_flags[n] = True
        elif led_state[n] == Colour.White: red_flags[n] = green_flags[n] = blue_flags[n] = True


# copies LED states to target states
def copy_state():

    global led_state, target_state

    for n in range(NUM_LEDS):
        target_state[n] = led_state[n]


# randomly shuffles LED states
def shuffle_state():

    global led_state

    for _ in range(4*NUM_LEDS):
        a = randrange(NUM_LEDS)
        b = randrange(NUM_LEDS)
        led_state[a], led_state[b] = led_state[b], led_state[a]


# returns True if LED states match target states
def test_completed():

    global led_state, target_state

    for n in range(NUM_LEDS):
        if led_state[n] != target_state[n]: return False
    return True


# rotates masked LEDs clockwise
def rotate_cw(mask = 0b111111):

    global led_state

    temp = []
    for n in range(NUM_LEDS):
        if mask & (1<<n): temp.append(led_state[n])
    item = temp[0]
    temp.pop(0)
    temp.append(item)
    i = 0
    for n in range(NUM_LEDS):
        if mask & (1<<n): led_state[n] = temp[i]; i += 1


# rotates masked LEDs counterclockwise
def rotate_ccw(mask = 0b111111):

    global led_state

    temp = []
    for n in range(NUM_LEDS):
        if mask & (1<<n): temp.append(led_state[n])
    item = temp[len(temp)-1]
    temp.pop(len(temp)-1)
    temp.insert(0, item)
    i = 0
    for n in range(NUM_LEDS):
        if mask & (1<<n): led_state[n] = temp[i]; i += 1


# rotate red components
def rotate_red():
    temp = red_flags[0]
    red_flags[0] = red_flags[1]
    red_flags[1] = red_flags[2]
    red_flags[2] = red_flags[3]
    red_flags[3] = red_flags[4]
    red_flags[4] = red_flags[5]
    red_flags[5] = temp

# rotate green components
def rotate_green():
    temp = green_flags[0]
    green_flags[0] = green_flags[1]
    green_flags[1] = green_flags[2]
    green_flags[2] = green_flags[3]
    green_flags[3] = green_flags[4]
    green_flags[4] = green_flags[5]
    green_flags[5] = temp

# rotate blue components
def rotate_blue():
    temp = blue_flags[0]
    blue_flags[0] = blue_flags[1]
    blue_flags[1] = blue_flags[2]
    blue_flags[2] = blue_flags[3]
    blue_flags[3] = blue_flags[4]
    blue_flags[4] = blue_flags[5]
    blue_flags[5] = temp


#------------------------------------------------------------------------
# puzzle #1
#------------------------------------------------------------------------

# make all LEDs white:
# rotary encoders move colour components clockwise and counterclockwise
# (rotary #1 moves red, #2 moves green, #3 moves blue)
# colour components combine and are 'sticky' if LED already on

def puzzle1_setup():

    global target_state, red_ndx, green_ndx, blue_ndx, red_flags, green_flags, blue_flags

    # fixed target pattern
    target_state = [Colour.White for _ in range(NUM_LEDS)]

    red_ndx = 0
    green_ndx = 2
    blue_ndx = 4

    red_flags = [True if n == red_ndx else False for n in range(NUM_LEDS)]
    green_flags = [True if n == green_ndx else False for n in range(NUM_LEDS)]
    blue_flags = [True if n == blue_ndx else False for n in range(NUM_LEDS)]

    draw_hexagon()
    draw_target_colours()

    draw_double_string(104, 52, "#1", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Make", "all leds", "white")


def puzzle1_loop():

    global red_ndx, green_ndx, blue_ndx, red_flags, green_flags, blue_flags

    sleep(LOOP_WAIT)

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        click()
        if not green_flags[red_ndx] and not blue_flags[red_ndx]: red_flags[red_ndx] = False;
        if pos1 > 0: red_ndx = (red_ndx - 1) % NUM_LEDS
        else: red_ndx = (red_ndx + 1) % NUM_LEDS
        red_flags[red_ndx] = True;
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        click()
        if not red_flags[green_ndx] and not blue_flags[green_ndx]: green_flags[green_ndx] = False;
        if pos2 > 0: green_ndx = (green_ndx - 1) % NUM_LEDS
        else: green_ndx = (green_ndx + 1) % NUM_LEDS
        green_flags[green_ndx] = True;
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        click()
        if not red_flags[blue_ndx] and not green_flags[blue_ndx]: blue_flags[blue_ndx] = False;
        if pos3 > 0: blue_ndx = (blue_ndx - 1) % NUM_LEDS
        else: blue_ndx = (blue_ndx + 1) % NUM_LEDS
        blue_flags[blue_ndx] = True;
        reset_rotary_position(3)

    for i in range(NUM_LEDS):
        red = DEFAULT_RGB_COMPONENT if red_flags[i] else 0
        green = DEFAULT_RGB_COMPONENT if green_flags[i] else 0
        blue = DEFAULT_RGB_COMPONENT if blue_flags[i] else 0
        set_led_rgb(i+1, red, green, blue, False)
    update_all_leds()

    white_cnt = 0
    for i in range(NUM_LEDS):
        if red_flags[i] and green_flags[i] and blue_flags[i]: white_cnt += 1
    if white_cnt == NUM_LEDS: return True
    else: return False


#------------------------------------------------------------------------
# puzzle #2
#------------------------------------------------------------------------

# match colour pattern:
# pushbuttons #1, #2, #3 introduce adjacent colours red, green, blue
# rotary encoders move/swap colours clockwise and counterclockwise

def puzzle2_setup():

    global led_state, target_state

    # random target pattern using red, green and blue
    target_state = [Colour.Red + randrange(3) for _ in range(NUM_LEDS)]

    # blank start pattern
    led_state = [Colour.Black for _ in range(NUM_LEDS)]

    draw_hexagon()
    draw_target_colours()

    draw_double_string(104, 52, "#2", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Match", "colour", "pattern")


def puzzle2_loop():

    global led_state

    sleep(LOOP_WAIT)

    if test_button_pressed(1) and led_state[1] != Colour.Red:
        short_beep()
        fade_out_led(2, FADE_WAIT)
        led_state[1] = Colour.Red
        set_led_colours(False)
        fade_in_led(2, FADE_WAIT)

    if test_button_pressed(2) and led_state[3] != Colour.Green:
        short_beep()
        fade_out_led(4, FADE_WAIT)
        led_state[3] = Colour.Green
        set_led_colours(False)
        fade_in_led(4, FADE_WAIT)

    if test_button_pressed(3) and led_state[5] != Colour.Blue:
        short_beep()
        fade_out_led(6, FADE_WAIT)
        led_state[5] = Colour.Blue
        set_led_colours(False)
        fade_in_led(6, FADE_WAIT)

    def swap(a, b):
        mask = (1<<a) | (1<<b)
        fade_out_masked_leds(mask, FADE_WAIT)
        led_state[a], led_state[b] = led_state[b], led_state[a]
        set_led_colours(False)
        fade_in_masked_leds(mask, FADE_WAIT)

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        click()
        if pos1 < 0:
            if led_state[0] == Colour.Black and led_state[5] != Colour.Black: swap (0, 5)
            elif led_state[0] != Colour.Black: swap(0, 1)
        else:
            if led_state[0] == Colour.Black and led_state[1] != Colour.Black: swap (0, 1)
            elif led_state[0] != Colour.Black: swap(0, 5)
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        click()
        if pos2 < 0:
            if led_state[2] == Colour.Black and led_state[1] != Colour.Black: swap (2, 1)
            elif led_state[2] != Colour.Black: swap(2, 3)
        else:
            if led_state[2] == Colour.Black and led_state[3] != Colour.Black: swap (2, 3)
            elif led_state[2] != Colour.Black: swap(2, 1)
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        click()
        if pos3 < 0:
            if led_state[4] == Colour.Black and led_state[3] != Colour.Black: swap (4, 3)
            elif led_state[4] != Colour.Black: swap(4, 5)
        else:
            if led_state[4] == Colour.Black and led_state[5] != Colour.Black: swap (4, 5)
            elif led_state[4] != Colour.Black: swap(4, 3)
        reset_rotary_position(3)

    return test_completed()


#------------------------------------------------------------------------
# puzzle #3
#------------------------------------------------------------------------

# match colour pattern:
# rotary encoders rotate all colours clockwise and counterclockwise
# pushbuttons freeze adjacent colour when rotating

def puzzle3_setup():

    global led_state, target_state

    # fixed target pattern
    target_state = [Colour.Red, Colour.Cyan, Colour.Blue, Colour.Yellow, Colour.Green, Colour.Magenta]

    # random start pattern
    while True:
        led_state = [target_state[n] for n in range(NUM_LEDS)]
        shuffle_state()
        if not test_completed(): break

    draw_hexagon()
    draw_target_colours()

    set_led_colours()

    draw_double_string(104, 52, "#3", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Match", "colour", "pattern")


def puzzle3_loop():

    global led_state

    sleep(LOOP_WAIT)

    mask = 0b111111
    if test_button_down(1): mask ^= (1<<1)
    if test_button_down(2): mask ^= (1<<3)
    if test_button_down(3): mask ^= (1<<5)

    for n in range(3):
        pos = get_rotary_position(n+1)
        if pos < -ROTARY_THRESHOLD or pos > +ROTARY_THRESHOLD:
            click()
            if pos < 0: rotate_ccw(mask)
            else: rotate_cw(mask)
            fade_out_masked_leds(mask, FADE_WAIT)
            set_led_colours(False)
            fade_in_masked_leds(mask, FADE_WAIT)
            reset_rotary_position(n+1)

    return test_completed()


#------------------------------------------------------------------------
# puzzle #4
#------------------------------------------------------------------------

# turn all LEDs off:
# pushbutton #1 turns adjacent LED off if red
# pushbutton #2 turns adjacent LED off if green
# pushbutton #3 turns adjacent LED off if blue
# rotary encoders rotate all LEDs clockwise or counterclockwise if adjacent LED not off

def puzzle4_setup():

    global led_state, target_state

    # blank target pattern
    target_state = [Colour.Black for _ in range(NUM_LEDS)]

    # random start pattern of red, green, blue
    led_state = [Colour.Red + randrange(3) for _ in range(NUM_LEDS)]

    draw_hexagon()
    draw_target_colours()

    set_led_colours()

    draw_double_string(104, 52, "#4", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Turn", "all leds", "off")


def puzzle4_loop():

    global led_state

    sleep(LOOP_WAIT)

    if test_button_pressed(1) and led_state[1] == Colour.Red:
        short_beep()
        fade_out_led(2, FADE_WAIT)
        led_state[1] = Colour.Black
        set_led_colours(False)

    if test_button_pressed(2) and led_state[3] == Colour.Green:
        short_beep()
        fade_out_led(4, FADE_WAIT)
        led_state[3] = Colour.Black
        set_led_colours(False)

    if test_button_pressed(3) and led_state[5] == Colour.Blue:
        short_beep()
        fade_out_led(6, FADE_WAIT)
        led_state[5] = Colour.Black
        set_led_colours(False)

    for n in range(3):
        pos = get_rotary_position(n+1)
        if pos < -ROTARY_THRESHOLD or pos > +ROTARY_THRESHOLD:
            if led_state[n*2] != Colour.Black:
                click()
                if pos < 0: rotate_ccw()
                else: rotate_cw()
                fade_out_masked_leds(wait = FADE_WAIT)
                set_led_colours(False)
                fade_in_masked_leds(wait = FADE_WAIT)
            reset_rotary_position(n+1)
            break

    return test_completed()


#------------------------------------------------------------------------
# puzzle #5
#------------------------------------------------------------------------

# stop all flashing on red:
# pushbuttons freeze adjacent LEDs if currently red
# rotary encoders freeze adjacent LEDs if currently red

def puzzle5_setup():

    global led_state, target_state, blink_time, time

    # start pattern
    led_state = [Colour.Red + randrange(6) for _ in range(NUM_LEDS)]

    # target pattern
    target_state = [Colour.Red for _ in range(NUM_LEDS)]

    # randomise blink times
    blink_time = [randrange(BLINK_STEPS) for _ in range(NUM_LEDS)]
    time = 0

    draw_hexagon()
    draw_target_colours()

    set_led_colours()

    draw_double_string(104, 52, "#5", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Stop", "flashing", "on red")


def puzzle5_loop():

    global led_state, blink_time, time

    sleep(float(BLINK_RES) / 1000)

    for n in range(NUM_LEDS):
        if time == blink_time[n]:
            if led_state[n] != Colour.Black:
                led_state[n] = Colour.Black
            else:
                # biased towards red
                i = randrange(8)
                if i > 5: i = 0
                led_state[n] = Colour.Red + i
            blink_time[n] = (blink_time[n] + 5 + randrange(20)) % BLINK_STEPS

    time = (time + 1) % BLINK_STEPS

    if test_button_pressed(1):
        if led_state[1] == Colour.Red and blink_time[1] != -1:
            blink_time[1] = -1
        else:
            led_state[1] = Colour.Black
            blink_time[1] = 0

    if test_button_pressed(2):
        if led_state[3] == Colour.Red and blink_time[3] != -1:
            blink_time[3] = -1
        else:
            led_state[3] = Colour.Black
            blink_time[3] = 0

    if test_button_pressed(3):
        if led_state[5] == Colour.Red and blink_time[5] != -1:
            blink_time[5] = -1
        else:
            led_state[5] = Colour.Black
            blink_time[5] = 0

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        click()
        if led_state[0] == Colour.Red and blink_time[0] != -1:
            blink_time[0] = -1
        else:
            led_state[0] = Colour.Black
            blink_time[0] = 0
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        click()
        if led_state[2] == Colour.Red and blink_time[2] != -1:
            blink_time[2] = -1
        else:
            led_state[2] = Colour.Black
            blink_time[2] = 0
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        click()
        if led_state[4] == Colour.Red and blink_time[4] != -1:
            blink_time[4] = -1
        else:
            led_state[4] = Colour.Black
            blink_time[4] = 0
        reset_rotary_position(3)

    set_led_colours(True)

    red_cnt = 0
    for n in range(NUM_LEDS):
        if blink_time[n] == -1: red_cnt += 1
    if test_button_down(): red_cnt = 0
    if red_cnt == NUM_LEDS: return True
    else: return False


#------------------------------------------------------------------------
# puzzle #6
#------------------------------------------------------------------------

# match colour pattern:
# rotary encoders rotate all LEDs clockwise or counterclockwise
# pushbuttons toggle colour bits
# solution: [i A-cw A-cw ii A-cw A-cw iii A-cw] repeat 6 times

def puzzle6_setup():

    global led_state, target_state

    # fixed target pattern
    target_state = [Colour.White for _ in range(NUM_LEDS)]

    led_state = [Colour.Black for _ in range(NUM_LEDS)]

    draw_hexagon()
    draw_target_colours()

    set_led_colours()

    draw_double_string(104, 52, "#6", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Match", "colour", "pattern")


def puzzle6_loop():

    global led_state, target_state

    sleep(LOOP_WAIT)

    for n in range(3):
        pos = get_rotary_position(n+1)
        if pos < -ROTARY_THRESHOLD or pos > +ROTARY_THRESHOLD:
            click()
            if pos < 0: rotate_ccw(0b111111)
            else: rotate_cw(0b111111)
            fade_out_masked_leds(0b111111, FADE_WAIT)
            set_led_colours(False)
            fade_in_masked_leds(0b111111, FADE_WAIT)
            reset_rotary_position(n+1)

    if test_button_pressed(1):
        short_beep()
        led_state[1] ^= (1<<0)

    if test_button_pressed(2):
        short_beep()
        led_state[3] ^= (1<<1)

    if test_button_pressed(3):
        short_beep()
        led_state[5] ^= (1<<2)

    set_led_colours(True)

    return test_completed()


#------------------------------------------------------------------------
# puzzle #7
#------------------------------------------------------------------------

# set all LEDs to the same colour:
# rotary encoders step through the colour of the adjacent LEDs
# pushbuttons set adjacent LEDs to average colour of LEDs either side
# solution: A-cw B-cw C-cw i ii iii

def puzzle7_setup():

    global led_state

    led_state = [Colour.Black for _ in range(NUM_LEDS)]

    draw_double_string(104, 52, "#7", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Set all", "leds to the", "same colour")


def puzzle7_loop():

    global led_state

    sleep(LOOP_WAIT)

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        click()
        if pos1 < 0:
            led_state[0] -= 1
            if led_state[0] < Colour.Red: led_state[0] = Colour.Yellow
        else:
            led_state[0] += 1
            if led_state[0] > Colour.Yellow: led_state[0] = Colour.Red
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        click()
        if pos2 < 0:
            led_state[2] -= 1
            if led_state[2] < Colour.Red: led_state[2] = Colour.Yellow
        else:
            led_state[2] += 1
            if led_state[2] > Colour.Yellow: led_state[2] = Colour.Red
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        click()
        if pos3 < 0:
            led_state[4] -= 1
            if led_state[4] < Colour.Red: led_state[4] = Colour.Yellow
        else:
            led_state[4] += 1
            if led_state[4] > Colour.Yellow: led_state[4] = Colour.Red
        reset_rotary_position(3)

    if test_button_pressed(1):
        short_beep()
        led_state[1] = (led_state[0] + led_state[2]) // 2

    if test_button_pressed(2):
        short_beep()
        led_state[3] = (led_state[2] + led_state[4]) // 2

    if test_button_pressed(3):
        short_beep()
        led_state[5] = (led_state[4] + led_state[0]) // 2

    set_led_colours(True)

    completed = True
    for n in range(NUM_LEDS-1):
        if led_state[n] == Colour.Black or led_state[n] != led_state[n+1]: completed = False
    return completed


#------------------------------------------------------------------------
# puzzle #8
#------------------------------------------------------------------------

# match colour pattern:
# pushbuttons increment and cycle adjacent and opposite LEDs
# adjacent colours cycle red -> green -> blue -> cyan -> magenta -> yellow
# opposite colours cycle as above plus black
# therefore synch changes with each complete cycle
# rotary encoders move LED colours to neighbouring LEDs
# but can be solved entirely using pushbuttons

def puzzle8_setup():

    global led_state, target_state

    # blank start pattern
    led_state = [Colour.Black for _ in range(NUM_LEDS)]

    # random target pattern of red, green, blue, cyan, magenta, yellow
    target_state = [Colour.Red + randrange(6) for _ in range(NUM_LEDS)]

    draw_hexagon()
    draw_target_colours()

    set_led_colours()

    draw_double_string(104, 52, "#8", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Match", "colour", "pattern")


def puzzle8_loop():

    global led_state

    sleep(LOOP_WAIT)

    if test_button_pressed(1):
        short_beep()
        fade_out_masked_leds(0b010010, FADE_WAIT)
        led_state[1] += 1
        if led_state[1] > Colour.Yellow: led_state[1] = Colour.Red
        led_state[4] += 1
        if led_state[4] > Colour.Yellow: led_state[4] = Colour.Black
        set_led_colours(False)
        fade_in_masked_leds(0b010010, FADE_WAIT)

    if test_button_pressed(2):
        short_beep()
        fade_out_masked_leds(0b001001, FADE_WAIT)
        led_state[3] += 1
        if led_state[3] > Colour.Yellow: led_state[3] = Colour.Red
        led_state[0] += 1
        if led_state[0] > Colour.Yellow: led_state[0] = Colour.Black
        set_led_colours(False)
        fade_in_masked_leds(0b001001, FADE_WAIT)

    if test_button_pressed(3):
        short_beep()
        fade_out_masked_leds(0b100100, FADE_WAIT)
        led_state[5] += 1
        if led_state[5] > Colour.Yellow: led_state[5] = Colour.Red
        led_state[2] += 1
        if led_state[2] > Colour.Yellow: led_state[2] = Colour.Black
        set_led_colours(False)
        fade_in_masked_leds(0b100100, FADE_WAIT)

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        if led_state[0] != Colour.Black:
            click()
            if pos1 < 0:
                fade_out_masked_leds(0b000011, FADE_WAIT)
                led_state[1] = led_state[0]
                led_state[0] = Colour.Black
                set_led_colours(False)
                fade_in_masked_leds(0b000011, FADE_WAIT)
            else:
                fade_out_masked_leds(0b10001, FADE_WAIT)
                led_state[5] = led_state[0]
                led_state[0] = Colour.Black
                set_led_colours(False)
                fade_in_masked_leds(0b100001, FADE_WAIT)
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        if led_state[2] != Colour.Black:
            click()
            if pos2 < 0:
                fade_out_masked_leds(0b001100, FADE_WAIT)
                led_state[3] = led_state[2]
                led_state[2] = Colour.Black
                set_led_colours(False)
                fade_in_masked_leds(0b001100, FADE_WAIT)
            else:
                fade_out_masked_leds(0b00110, FADE_WAIT)
                led_state[1] = led_state[2]
                led_state[2] = Colour.Black
                set_led_colours(False)
                fade_in_masked_leds(0b000110, FADE_WAIT)
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        if led_state[4] != Colour.Black:
            click()
            if pos3 < 0:
                fade_out_masked_leds(0b110000, FADE_WAIT)
                led_state[5] = led_state[4]
                led_state[4] = Colour.Black
                set_led_colours(False)
                fade_in_masked_leds(0b110000, FADE_WAIT)
            else:
                fade_out_masked_leds(0b011000, FADE_WAIT)
                led_state[3] = led_state[4]
                led_state[4] = Colour.Black
                set_led_colours(False)
                fade_in_masked_leds(0b011000, FADE_WAIT)
        reset_rotary_position(3)

    return test_completed()


#------------------------------------------------------------------------
# puzzle #9
#------------------------------------------------------------------------

# synchronise blinking of all LEDs:
# colours are not significant
# LEDs blink at 1Hz with 50% duty cycle
# pushbuttons hold adjacent LEDs on until released
# rotary encoders advance or retreat blink phase of adjacent LEDs

def puzzle9_setup():

    global led_state, blink_time, time

    led_state = [Colour.Black for _ in range(NUM_LEDS)]

    # randomise blink times
    blink_time = [randrange(BLINK_STEPS) for _ in range(NUM_LEDS)]
    time = 0

    draw_double_string(104, 52, "#9", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Synchronise", "blinking of", "all leds")


def puzzle9_loop():

    global led_state, blink_time, time

    sleep(float(BLINK_RES) / 1000)

    for n in range(NUM_LEDS):
        t1 = blink_time[n]; t2 = (t1 + BLINK_STEPS/2) % BLINK_STEPS
        led_state[n] = Colour.Black
        if blink_time[n] < BLINK_STEPS/2:
            if time >= t1 and time < t2: led_state[n] = Colour.Red + n
        else:
            if time >= t1 or time < t2: led_state[n] = Colour.Red + n

    if test_button_down(1):
        led_state[1] = Colour.Red + 1
        blink_time[1] = time

    if test_button_down(2):
        led_state[3] = Colour.Red + 3
        blink_time[3] = time

    if test_button_down(3):
        led_state[5] = Colour.Red + 5
        blink_time[5] = time

    time = (time + 1) % BLINK_STEPS

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        click()
        if pos1 < 0: blink_time[0] = (blink_time[0] - 1) % BLINK_STEPS
        else: blink_time[0] = (blink_time[0] + 1) % BLINK_STEPS
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        click()
        if pos2 < 0: blink_time[2] = (blink_time[2] - 1) % BLINK_STEPS
        else: blink_time[2] = (blink_time[2] + 1) % BLINK_STEPS
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        click()
        if pos3 < 0: blink_time[4] = (blink_time[4] - 1) % BLINK_STEPS
        else: blink_time[4] = (blink_time[4] + 1) % BLINK_STEPS
        reset_rotary_position(3)

    set_led_colours(True)

    synch = True
    if test_button_down(): synch = False
    for n in range(NUM_LEDS):
        d = blink_time[n] - blink_time[0]
        if d > BLINK_STEPS/2: d = BLINK_STEPS - d
        elif d < -BLINK_STEPS/2: d = BLINK_STEPS + d
        if abs(d) > 2: synch = False
    if synch:
        for n in range(NUM_LEDS): led_state[n] = Colour.Red + n
        set_led_colours(True)
        sleep(1)
        fade_out_masked_leds(wait = FADE_WAIT)
        return True
    else:
        return False


#------------------------------------------------------------------------
# puzzle #10
#------------------------------------------------------------------------

# match colour pattern:
# pushbutton #1, #2, #3 turns opposite LED red, green, blue
# rotary encoders 'push' colour components clockwise or counterclockwise
# hint: set Y, M, C first then R, G, B
# solution: i C-ccw ii A-ccw iii B-ccw i C-cw ii A-cw iii B-cw i ii iii

def puzzle10_setup():

    global led_state, target_state, red_flags, green_flags, blue_flags

    # blank start pattern
    led_state = [Colour.Black for _ in range(NUM_LEDS)]
    red_flags = [False for _ in range(NUM_LEDS)]
    green_flags = [False for _ in range(NUM_LEDS)]
    blue_flags = [False for _ in range(NUM_LEDS)]

    # fixed target pattern
    target_state = [Colour.Green, Colour.Cyan, Colour.Blue, Colour.Magenta, Colour.Red, Colour.Yellow]

    draw_hexagon()
    draw_target_colours()

    set_led_colours()

    draw_double_string(96, 52, "#10", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Match", "colour", "pattern")


def puzzle10_loop():

    global led_state, red_flags, green_flags, blue_flags

    sleep(LOOP_WAIT)

    if test_button_pressed(1):
        short_beep()
        red_flags[4] = True
        green_flags[4] = False
        blue_flags[4] = False
        flags_to_state()
        set_led_colours(False)
        fade_in_masked_leds(1<<4, FADE_WAIT)

    if test_button_pressed(2):
        short_beep()
        red_flags[0] = False
        green_flags[0] = True
        blue_flags[0] = False
        flags_to_state()
        set_led_colours(False)
        fade_in_masked_leds(1<<0, FADE_WAIT)

    if test_button_pressed(3):
        short_beep()
        red_flags[2] = False
        green_flags[2] = False
        blue_flags[2] = True
        flags_to_state()
        set_led_colours(False)
        fade_in_masked_leds(1<<2, FADE_WAIT)

    def push(ndx, step):
        mask = 0

        if red_flags[ndx]:
            red_flags[ndx] = False
            mask |= (1<<ndx)
            ndx1 = ndx
            while True:
                ndx1 = (ndx1 + step) % NUM_LEDS
                mask |= (1<<ndx1)
                if not red_flags[ndx1]:
                    red_flags[ndx1] = True
                    break
                if ndx1 == ndx: break

        if green_flags[ndx]:
            green_flags[ndx] = False
            mask |= (1<<ndx)
            ndx1 = ndx
            while True:
                ndx1 = (ndx1 + step) % NUM_LEDS
                mask |= (1<<ndx1)
                if not green_flags[ndx1]:
                    green_flags[ndx1] = True
                    break
                if ndx1 == ndx: break

        if blue_flags[ndx]:
            blue_flags[ndx] = False
            mask |= (1<<ndx)
            ndx1 = ndx
            while True:
                ndx1 = (ndx1 + step) % NUM_LEDS
                mask |= (1<<ndx1)
                if not blue_flags[ndx1]:
                    blue_flags[ndx1] = True
                    break
                if ndx1 == ndx: break

        if mask != 0:
            fade_out_masked_leds(mask, FADE_WAIT)
            flags_to_state()
            set_led_colours(False)
            fade_in_masked_leds(mask, FADE_WAIT)

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        click()
        if pos1 < 0: push(0, +1)
        else: push(0, -1)
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        click()
        if pos2 < 0: push(2, +1)
        else: push(2, -1)
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        click()
        if pos3 < 0: push(4, +1)
        else: push(4, -1)
        reset_rotary_position(3)

    return test_completed()


#------------------------------------------------------------------------
# puzzle #11
#------------------------------------------------------------------------

# match colour pattern:
# pushbuttons swap LEDs either side
# rotary encoders move adjacent LED and left or right LED clockwise or counterclockwise
# but only if adjacent colour matches in direction of movement
# easy to fall into trap
# solution: C-cw i B-cw A-cw i

def puzzle11_setup():

    global led_state, target_state

    # fixed start pattern
    led_state = [Colour.Orange, Colour.Orange, Colour.Pink, Colour.Pink, Colour.Pink, Colour.Orange]

    # fixed target pattern
    target_state = [Colour.Pink, Colour.Pink, Colour.Orange, Colour.Orange, Colour.Orange, Colour.Pink]

    draw_hexagon()
    draw_target_colours()

    set_led_colours()

    draw_double_string(96, 52, "#11", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Match", "colour", "pattern")


def puzzle11_loop():

    global led_state

    sleep(LOOP_WAIT)

    if test_button_pressed(1):
        short_beep()
        mask = 0b000101
        fade_out_masked_leds(mask, FADE_WAIT)
        led_state[0], led_state[2] = led_state[2], led_state[0]
        set_led_colours(False)
        fade_in_masked_leds(mask, FADE_WAIT)

    if test_button_pressed(2):
        short_beep()
        mask = 0b010100
        fade_out_masked_leds(mask, FADE_WAIT)
        led_state[2], led_state[4] = led_state[4], led_state[2]
        set_led_colours(False)
        fade_in_masked_leds(mask, FADE_WAIT)

    if test_button_pressed(3):
        short_beep()
        mask = 0b010001
        fade_out_masked_leds(mask, FADE_WAIT)
        led_state[4], led_state[0] = led_state[0], led_state[4]
        set_led_colours(False)
        fade_in_masked_leds(mask, FADE_WAIT)

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        mask = 0b100011
        if pos1 < 0 and led_state[0] == led_state[1]: rotate_ccw(mask)
        elif pos1 > 0 and led_state[0] == led_state[5]: rotate_cw(mask)
        else: mask = 0
        if mask != 0:
            click()
            fade_out_masked_leds(mask, FADE_WAIT)
            set_led_colours(False)
            fade_in_masked_leds(mask, FADE_WAIT)
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        mask = 0b001110
        if pos2 < 0 and led_state[2] == led_state[3]: rotate_ccw(mask)
        elif pos2 > 0 and led_state[2] == led_state[1]: rotate_cw(mask)
        else: mask = 0
        if mask != 0:
            click()
            fade_out_masked_leds(mask, FADE_WAIT)
            set_led_colours(False)
            fade_in_masked_leds(mask, FADE_WAIT)
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        mask = 0b111000
        if pos3 < 0 and led_state[4] == led_state[5]: rotate_ccw(mask)
        elif pos3 > 0 and led_state[4] == led_state[3]: rotate_cw(mask)
        else: mask = 0
        if mask != 0:
            click()
            fade_out_masked_leds(mask, FADE_WAIT)
            set_led_colours(False)
            fade_in_masked_leds(mask, FADE_WAIT)
        reset_rotary_position(3)

    return test_completed()


#------------------------------------------------------------------------
# puzzle #12
#------------------------------------------------------------------------

# freeze all LEDs on a single colour:
# pushbuttons freeze opposite LEDs if same colour

def puzzle12_setup():

    global led_state, blink_time

    led_state = [Colour.Black for _ in range(NUM_LEDS)]

    blink_time = [0 for _ in range(NUM_LEDS)]

    draw_double_string(96, 52, "#12", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Freeze all", "leds on a", "single colour")


def puzzle12_loop():

    global led_state, blink_time

    sleep(LOOP_WAIT)

    frozen = 0
    for n in range(NUM_LEDS):
        if blink_time[n] < 0:
            colour = led_state[n]
            frozen += 1

    for n in range(NUM_LEDS):
        if blink_time[n] == 0:
            blink_time[n] = 5 + randrange(15)
            led_state[n] = Colour.Red + randrange(NUM_LEDS)
            if frozen >= 4 and randrange(4) == 0: led_state[n] = colour
            elif frozen >= 2 and randrange(6) == 0: led_state[n] = colour
        elif blink_time[n] > 0:
            blink_time[n] -= 1

    if test_button_pressed(1):
        short_beep()
        if blink_time[1] == -1:
            blink_time[1] = blink_time[4] = 0
        elif led_state[1] == led_state[4]:
            blink_time[1] = blink_time[4] = -1

    if test_button_pressed(2):
        short_beep()
        if blink_time[3] == -1:
            blink_time[3] = blink_time[0] = 0
        elif led_state[3] == led_state[0]:
            blink_time[3] = blink_time[0] = -1

    if test_button_pressed(3):
        short_beep()
        if blink_time[5] == -1:
            blink_time[5] = blink_time[2] = 0
        elif led_state[5] == led_state[2]:
            blink_time[5] = blink_time[2] = -1

    set_led_colours(True)

    completed = True
    for n in range(NUM_LEDS-1):
        if blink_time[n] != -1 or led_state[n] != led_state[n+1]: completed = False
    return completed


#------------------------------------------------------------------------
# puzzle #13
#------------------------------------------------------------------------

# match colour pattern:
# rotary encoders rotate red (A), green (B) and blue (C) components clockwise or counterclockwise

def puzzle13_setup():

    global led_state, target_state, red_flags, green_flags, blue_flags

    led_state = [Colour.Black for _ in range(NUM_LEDS)]
    target_state = [Colour.Black for _ in range(NUM_LEDS)]

    # random target pattern
    red_flags = [randrange(3) == 0 for _ in range(NUM_LEDS)]
    green_flags = [randrange(3) == 0 for _ in range(NUM_LEDS)]
    blue_flags = [randrange(3) == 0 for _ in range(NUM_LEDS)]
    flags_to_state()
    copy_state()

    # randomly rotate components
    for _ in range(1 + randrange(4)): rotate_red()
    for _ in range(1 + randrange(4)): rotate_green()
    for _ in range(1 + randrange(4)): rotate_blue()
    flags_to_state()

    draw_hexagon()
    draw_target_colours()

    set_led_colours()

    draw_double_string(96, 52, "#13", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Match", "colour", "pattern")


def puzzle13_loop():

    global led_state

    sleep(LOOP_WAIT)

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        click()
        if pos1 < 0:
            rotate_red()
            rotate_red()
            rotate_red()
            rotate_red()
            rotate_red()
        else:
            rotate_red()
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        click()
        if pos2 < 0:
            rotate_green()
            rotate_green()
            rotate_green()
            rotate_green()
            rotate_green()
        else:
            rotate_green()
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        click()
        if pos3 < 0:
            rotate_blue()
            rotate_blue()
            rotate_blue()
            rotate_blue()
            rotate_blue()
        else:
            rotate_blue()
        reset_rotary_position(3)

    flags_to_state()
    set_led_colours(True)

    return test_completed()


#------------------------------------------------------------------------
# puzzle #14
#------------------------------------------------------------------------

# match colour pattern:
# rotary encoders move RGB colour components clockwise and counterclockwise
# red component moved first, then green, then blue
# move blocked if same colour component already set
# hint: position blue first, then green, then red

def puzzle14_setup():

    global led_state, target_state, red_flags, green_flags, blue_flags

    red_flags = [False for _ in range(NUM_LEDS)]
    green_flags = [False for _ in range(NUM_LEDS)]
    blue_flags = [False for _ in range(NUM_LEDS)]

    # fixed target pattern
    target_state = [Colour.Red, Colour.Green, Colour.Blue, Colour.Red, Colour.Green, Colour.Blue]

    # random start pattern
    while True:
        led_state = [target_state[n] for n in range(NUM_LEDS)]
        shuffle_state()
        if not test_completed(): break
    state_to_flags()

    draw_hexagon()
    draw_target_colours()

    set_led_colours()

    draw_double_string(96, 52, "#14", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Match", "colour", "pattern")


def puzzle14_loop():

    global led_state, red_flags, green_flags, blue_flags

    sleep(LOOP_WAIT)

    def combine1(ndx1, ndx2, ndx3):

        if not red_flags[ndx2] and red_flags[ndx1]:
            red_flags[ndx1] = False
            red_flags[ndx2] = True
            mask = (1<<ndx1) | (1<<ndx2)
        elif red_flags[ndx2] and not red_flags[ndx3]:
            red_flags[ndx2] = False
            red_flags[ndx3] = True
            mask = (1<<ndx2) | (1<<ndx3)

        elif not green_flags[ndx2] and green_flags[ndx1]:
            green_flags[ndx1] = False
            green_flags[ndx2] = True
            mask = (1<<ndx1) | (1<<ndx2)
        elif green_flags[ndx2] and not green_flags[ndx3]:
            green_flags[ndx2] = False
            green_flags[ndx3] = True
            mask = (1<<ndx2) | (1<<ndx3)

        elif not blue_flags[ndx2] and blue_flags[ndx1]:
            blue_flags[ndx1] = False
            blue_flags[ndx2] = True
            mask = (1<<ndx1) | (1<<ndx2)
        elif blue_flags[ndx2] and not blue_flags[ndx3]:
            blue_flags[ndx2] = False
            blue_flags[ndx3] = True
            mask = (1<<ndx2) | (1<<ndx3)

        else:
            return

        fade_out_masked_leds(mask, FADE_WAIT)
        flags_to_state()
        set_led_colours(False)
        fade_in_masked_leds(mask, FADE_WAIT)

    def combine2(ndx1, ndx2, ndx3):

        if not red_flags[ndx2] and red_flags[ndx1]:
            red_flags[ndx1] = False
            red_flags[ndx2] = True
            mask = (1<<ndx1) | (1<<ndx2)
        elif red_flags[ndx2] and not red_flags[ndx3]:
            red_flags[ndx2] = False
            red_flags[ndx3] = True
            mask = (1<<ndx2) | (1<<ndx3)

        elif not green_flags[ndx2] and green_flags[ndx1]:
            green_flags[ndx1] = False
            green_flags[ndx2] = True
            mask = (1<<ndx1) | (1<<ndx2)
        elif green_flags[ndx2] and not green_flags[ndx3]:
            green_flags[ndx2] = False
            green_flags[ndx3] = True
            mask = (1<<ndx2) | (1<<ndx3)

        elif not blue_flags[ndx2] and blue_flags[ndx1]:
            blue_flags[ndx1] = False
            blue_flags[ndx2] = True
            mask = (1<<ndx1) | (1<<ndx2)
        elif blue_flags[ndx2] and not blue_flags[ndx3]:
            blue_flags[ndx2] = False
            blue_flags[ndx3] = True
            mask = (1<<ndx2) | (1<<ndx3)

        else:
            return

        fade_out_masked_leds(mask, FADE_WAIT)
        flags_to_state()
        set_led_colours(False)
        fade_in_masked_leds(mask, FADE_WAIT)

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        click()
        if pos1 < 0: combine1(5, 0, 1)
        else: combine2(1, 0, 5)
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        click()
        if pos2 < 0: combine1(1, 2, 3)
        else: combine2(3, 2, 1)
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        click()
        if pos3 < 0: combine1(3, 4, 5)
        else: combine2(5, 4, 3)
        reset_rotary_position(3)

    return test_completed()


#------------------------------------------------------------------------
# puzzle #15
#------------------------------------------------------------------------

# match colour pattern:
# pushbuttons swap opposite LEDs
# rotary encoders swap adjacent LED and left or right LED clockwise or counterclockwise
# but only if adjacent colour is higher 'rank'

def puzzle15_setup():

    global led_state, target_state

    # fixed target pattern
    target_state = [Colour.Red, Colour.Green, Colour.Blue, Colour.Cyan, Colour.Magenta, Colour.Yellow]

    # random start pattern
    while True:
        led_state = [target_state[n] for n in range(NUM_LEDS)]
        shuffle_state()
        if not test_completed(): break

    draw_hexagon()
    draw_target_colours()

    set_led_colours()

    draw_double_string(96, 52, "#15", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Match", "colour", "pattern")


def puzzle15_loop():

    global led_state

    sleep(LOOP_WAIT)

    def swap(a, b, rank = True):
        state_a = led_state[a]
        state_b = led_state[b]
        if rank and state_a < state_b: return
        mask = (1<<a) | (1<<b)
        fade_out_masked_leds(mask, FADE_WAIT)
        led_state[a], led_state[b] = led_state[b], led_state[a]
        set_led_colours(False)
        fade_in_masked_leds(mask, FADE_WAIT)

    if test_button_pressed(1):
        short_beep()
        swap(1, 4, False)

    if test_button_pressed(2):
        short_beep()
        swap(3, 0, False)

    if test_button_pressed(3):
        short_beep()
        swap(5, 2, False)

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        click()
        if pos1 < 0: swap(0, 1)
        else: swap(0, 5)
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        click()
        if pos2 < 0: swap(2, 3)
        else: swap(2, 1)
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        click()
        if pos3 < 0: swap(4, 5)
        else: swap(4, 3)
        reset_rotary_position(3)

    return test_completed()


#------------------------------------------------------------------------
# puzzle #16
#------------------------------------------------------------------------

# set all LEDs to the same colour:
# rotary encoders step through the colour of the adjacent and the left and right LEDs
# solution: C-cw A-ccw A-cw B-ccw B-cw

def puzzle16_setup():

    global led_state

    led_state = [Colour.Black for _ in range(NUM_LEDS)]

    draw_double_string(96, 52, "#16", LCD_RED, LCD_BLACK)
    draw_instructions(80, "Set all", "leds to the", "same colour")


def puzzle16_loop():

    global led_state

    sleep(LOOP_WAIT)

    pos1 = get_rotary_position(1)
    if pos1 < -ROTARY_THRESHOLD or pos1 > +ROTARY_THRESHOLD:
        click()
        if pos1 < 0:
            led_state[0] -= 1
            if led_state[0] < Colour.Red: led_state[0] = Colour.Yellow
            led_state[1] -= 1
            if led_state[1] < Colour.Red: led_state[1] = Colour.Yellow
            led_state[5] -= 1
            if led_state[5] < Colour.Red: led_state[5] = Colour.Yellow
        else:
            led_state[0] += 1
            if led_state[0] > Colour.Yellow: led_state[0] = Colour.Red
            led_state[1] += 1
            if led_state[1] > Colour.Yellow: led_state[1] = Colour.Red
            led_state[5] += 1
            if led_state[5] > Colour.Yellow: led_state[5] = Colour.Red
        reset_rotary_position(1)

    pos2 = get_rotary_position(2)
    if pos2 < -ROTARY_THRESHOLD or pos2 > +ROTARY_THRESHOLD:
        click()
        if pos2 < 0:
            led_state[2] -= 1
            if led_state[2] < Colour.Red: led_state[2] = Colour.Yellow
            led_state[1] -= 1
            if led_state[1] < Colour.Red: led_state[1] = Colour.Yellow
            led_state[3] -= 1
            if led_state[3] < Colour.Red: led_state[3] = Colour.Yellow
        else:
            led_state[2] += 1
            if led_state[2] > Colour.Yellow: led_state[2] = Colour.Red
            led_state[1] += 1
            if led_state[1] > Colour.Yellow: led_state[1] = Colour.Red
            led_state[3] += 1
            if led_state[3] > Colour.Yellow: led_state[3] = Colour.Red
        reset_rotary_position(2)

    pos3 = get_rotary_position(3)
    if pos3 < -ROTARY_THRESHOLD or pos3 > +ROTARY_THRESHOLD:
        click()
        if pos3 < 0:
            led_state[4] -= 1
            if led_state[4] < Colour.Red: led_state[4] = Colour.Yellow
            led_state[3] -= 1
            if led_state[3] < Colour.Red: led_state[3] = Colour.Yellow
            led_state[5] -= 1
            if led_state[5] < Colour.Red: led_state[5] = Colour.Yellow
        else:
            led_state[4] += 1
            if led_state[4] > Colour.Yellow: led_state[4] = Colour.Red
            led_state[3] += 1
            if led_state[3] > Colour.Yellow: led_state[3] = Colour.Red
            led_state[5] += 1
            if led_state[5] > Colour.Yellow: led_state[5] = Colour.Red
        reset_rotary_position(3)

    set_led_colours(True)

    completed = True
    for n in range(NUM_LEDS-1):
        if led_state[n] == Colour.Black or led_state[n] != led_state[n+1]: completed = False
    return completed


#------------------------------------------------------------------------
# puzzle executive
#------------------------------------------------------------------------

def select_puzzle():

    global current_puzzle

    clear_display()

    reset_all_leds()

    draw_instructions(54, "Select", "a", "puzzle")

    def _draw_puzzle_number():

        x = 72 if current_puzzle < 10 else 60; y = 140
        x = draw_triple_string(x, y, " #", LCD_RED, LCD_BLACK)
        x = draw_triple_decimal(x, y, current_puzzle, LCD_RED, LCD_BLACK)
        draw_triple_string(x, y, " ", LCD_RED, LCD_BLACK)

    _draw_puzzle_number()

    while True:

        sleep(LOOP_WAIT)

        for n in range(3):
            pos = get_rotary_position(n+1)
            if pos < -ROTARY_THRESHOLD or pos > +ROTARY_THRESHOLD:
                click()
                if pos < 0:
                    current_puzzle -= 1
                    if current_puzzle < 1: current_puzzle = NUM_PUZZLES
                    _draw_puzzle_number()
                else:
                    current_puzzle += 1
                    if current_puzzle > NUM_PUZZLES: current_puzzle = 1
                    _draw_puzzle_number()
                reset_rotary_position(n+1)

        if test_button_pressed():
            short_beep()
            break


def puzzle_setup():

    clear_display()

    reset_all_leds()

    reset_rotary_position(1)
    reset_rotary_position(2)
    reset_rotary_position(3)

    led_state = [Colour.Black for _ in range(NUM_LEDS)]

    red_flags = [False for _ in range(NUM_LEDS)]
    green_flags = [False for _ in range(NUM_LEDS)]
    blue_flags = [False for _ in range(NUM_LEDS)]

    # seed random number generator
    seed()

    # garbage collect
    collect()

    select_puzzle()

    clear_display()

    if current_puzzle == 1: puzzle1_setup()
    elif current_puzzle == 2: puzzle2_setup()
    elif current_puzzle == 3: puzzle3_setup()
    elif current_puzzle == 4: puzzle4_setup()
    elif current_puzzle == 5: puzzle5_setup()
    elif current_puzzle == 6: puzzle6_setup()
    elif current_puzzle == 7: puzzle7_setup()
    elif current_puzzle == 8: puzzle8_setup()
    elif current_puzzle == 9: puzzle9_setup()
    elif current_puzzle == 10: puzzle10_setup()
    elif current_puzzle == 11: puzzle11_setup()
    elif current_puzzle == 12: puzzle12_setup()
    elif current_puzzle == 13: puzzle13_setup()
    elif current_puzzle == 14: puzzle14_setup()
    elif current_puzzle == 15: puzzle15_setup()
    elif current_puzzle == 16: puzzle16_setup()

    # wait for pushbuttons to be released
    while test_button_down(): pass


def puzzle_loop():

    if current_puzzle == 1: return puzzle1_loop()
    elif current_puzzle == 2: return puzzle2_loop()
    elif current_puzzle == 3: return puzzle3_loop()
    elif current_puzzle == 4: return puzzle4_loop()
    elif current_puzzle == 5: return puzzle5_loop()
    elif current_puzzle == 6: return puzzle6_loop()
    elif current_puzzle == 7: return puzzle7_loop()
    elif current_puzzle == 8: return puzzle8_loop()
    elif current_puzzle == 9: return puzzle9_loop()
    elif current_puzzle == 10: return puzzle10_loop()
    elif current_puzzle == 11: return puzzle11_loop()
    elif current_puzzle == 12: return puzzle12_loop()
    elif current_puzzle == 13: return puzzle13_loop()
    elif current_puzzle == 14: return puzzle14_loop()
    elif current_puzzle == 15: return puzzle15_loop()
    elif current_puzzle == 16: return puzzle16_loop()
    else: return False


def puzzle_solved():

    # wait for pushbuttons to be released
    while test_button_down(): pass

    while True:
        # flash message
        draw_double_string(64, 150, "Solved!", LCD_BLUE, LCD_BLACK)
        disable_rotaries()
        play_sfx(SFX_SOLVED)
        enable_rotaries()
        if test_button_down(): return
        draw_double_string(64, 150, "       ", LCD_BLUE, LCD_BLACK)
        for _ in range(5):
            sleep(0.1)
            if test_button_down(): return


# wait for pushbutton to be pressed
while not test_button_down(): pass
short_beep()

while True:

    puzzle_setup()

    solved = False

    while True:

        # any two pushbuttons to exit to menu
        if test_break():
            reset_all_leds()
            clear_display()
            break

        solved = puzzle_loop()
        if solved: break

    if solved: puzzle_solved()

    # wait for pushbuttons to be released
    while test_button_down(): pass
