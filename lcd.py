#############################################################################
# FILE:      lcd.py															#
# CONTENTS:  LCD display module												#
# COPYRIGHT: MadLab Ltd. 2026												#
# AUTHOR:    James Hutchby  												#
# UPDATED:   10/04/26   													#
#############################################################################

from machine import Pin
from rp2 import PIO, StateMachine, asm_pio
from time import sleep, sleep_us

from font import font


#------------------------------------------------------------------------
# PIO
#------------------------------------------------------------------------

@asm_pio(out_init=PIO.OUT_LOW, sideset_init=PIO.OUT_HIGH, side_pindir=False, out_shiftdir=PIO.SHIFT_LEFT,
  autopull=False, pull_thresh=8, fifo_join=PIO.JOIN_TX)
def _tx_8():

    pull(block).side(1)
    set(y, 7).side(1)
    label('loop1')
    out(pins, 1).side(0)
    jmp(y_dec, 'loop1').side(1)


@asm_pio(out_init=PIO.OUT_LOW, sideset_init=PIO.OUT_HIGH, side_pindir=False, out_shiftdir=PIO.SHIFT_LEFT,
  autopull=False, pull_thresh=16, fifo_join=PIO.JOIN_TX)
def _tx_16():

    pull(block).side(1)
    set(y, 15).side(1)
    label('loop2')
    out(pins, 1).side(0)
    jmp(y_dec, 'loop2').side(1)


@asm_pio(out_init=PIO.OUT_LOW, sideset_init=PIO.OUT_HIGH, side_pindir=False, out_shiftdir=PIO.SHIFT_LEFT,
  autopull=False, pull_thresh=32, fifo_join=PIO.JOIN_TX)
def _tx_32():

    pull(block).side(1)
    set(y, 31).side(1)
    label('loop3')
    out(pins, 1).side(0)
    jmp(y_dec, 'loop3').side(1)


#------------------------------------------------------------------------
# port assignments (GPIO numbers)
#------------------------------------------------------------------------

SCL_PIN = const(19)			# serial clock (active low)
SDA_PIN = const(20)			# serial data
DC_PIN = const(21)			# data/command (high = data, low = command)
CS_PIN = const(22)			# chip select (active low)
RES_PIN = const(26)			# reset (active low)


#------------------------------------------------------------------------
# constants
#------------------------------------------------------------------------

LCD_WIDTH = const(240)				# display width in pixels
LCD_HEIGHT = const(240)				# display height in pixels

LCD_BLACK = const(0x0000_0000)		# standard colours
LCD_RED = const(0xf800_f800)
LCD_GREEN = const(0x07e0_07e0)
LCD_BLUE = const(0x001f_0001f)
LCD_CYAN = const(0x07ff_07ff)
LCD_MAGENTA = const(0xf81f_f81f)
LCD_YELLOW = const(0xffe0_ffe0)
LCD_WHITE = const(0xffff_ffff)
LCD_ORANGE = const(0xfb00_fb00)
LCD_PINK = const(0xfa35_fa35)

SPI_SPEED = const(48_000_000)		# SPI speed in Hz

LCD_SM1 = 0							# state machines
LCD_SM2 = 1
LCD_SM3 = 2


#------------------------------------------------------------------------
# GC9A01 commands
#------------------------------------------------------------------------

SWRESET = const(0x01)				# software reset (not documented)

# level 1
RDDID = const(0x04)					# read display identification information
RDDST = const(0x09)					# read display status
SLPOUT = const(0x11)				# sleep out mode
PTLON = const(0x12)					# partial mode on
NORON = const(0x13)					# normal display mode on
INVOFF = const(0x20)				# display inversion off
INVON = const(0x21)					# display inversion on
DISPOFF = const(0x28)				# display off
DISPON = const(0x29)				# display on
CASET = const(0x2a)					# column address set
RASET = const(0x2b)					# row address set
RAMWR = const(0x2c)					# memory write
PTLAR = const(0x30)					# partial area
VSCRDEF = const(0x33)				# vertical scrolling definition
TEOFF = const(0x34)					# tearing effect line off
TEON = const(0x35)					# tearing effect line on
MADCTL = const(0x36)				# memory access control
VSCSAD = const(0x37)				# vertical scrolling start address
IDMOFF = const(0x38)				# idle mode off
IDMON = const(0x39)					# idle mode on
COLMOD = const(0x3a)				# pixel format set
WRMEMC = const(0x3c)				# write memory continue
STE = const(0x44)					# set tear scanline
GSCAN = const(0x45)					# get scanline
WRDISBV = const(0x51)				# write display brightness
WRCTRLD = const(0x53)				# write CTRL display
RDID1 = const(0xda)					# read ID1
RDID2 = const(0xdb)					# read ID2
RDID3 = const(0xdc)					# read ID3

# level 2
RGB_CONTROL = const(0xb0)			# RGB interface signal control
BLANKING_CONTROL = const(0xb5)		# blanking porch control
DISPLAY_CONTROL = const(0xb6)		# display function control
TEARING_CONTROL = const(0xba)		# tearing effect control
INTERFACE_CONTROL = const(0xf6)		# interface control

# level 3
FRAMERATE = const(0xe8)				# frame rate
SPI2DATA = const(0xe9)				# SPI 2DATA control
POWER_CONTROL1 = const(0xc1)		# power control 1
POWER_CONTROL2 = const(0xc3)		# power control 2
POWER_CONTROL3 = const(0xc4)		# power control 3
POWER_CONTROL4 = const(0xc9)		# power control 4
POWER_CONTROL7 = const(0xa7)		# power control 7
INTER_ENABLE1 = const(0xfe)			# inter register enable1
INTER_ENABLE2 = const(0xef)			# inter register enable2
SET_GAMMA1 = const(0xf0)			# set gamma1
SET_GAMMA2 = const(0xf1)			# set gamma2
SET_GAMMA3 = const(0xf2)			# set gamma3
SET_GAMMA4 = const(0xf3)			# set gamma4

MADCTL_MY = const(1<<7)				# page address order
MADCTL_MX = const(1<<6)				# column address order
MADCTL_MV = const(1<<5)				# page/column order
MADCTL_ML = const(1<<4)				# line address order
MADCTL_RGB = const(0<<3)			# RGB order
MADCTL_BGR = const(1<<3)			# BGR order
MADCTL_MH = const(1<<2)				# display data latch order


#------------------------------------------------------------------------
# functions
#------------------------------------------------------------------------

# transmits a command byte to the display
@micropython.native
def _tx_command(b):
    global dc, sm1
    dc.low()
    sm1.put(b << 24)
    sleep_us(1)

# transmits a data byte to the display
@micropython.native
def _tx_data(b):
    global dc, sm1
    dc.high()
    sm1.put(b << 24)


# sets display addresses prior to writing to the display
@micropython.native
def _set_addrs(x1, x2, y1, y2):

    global dc, sm1, sm2, sm3

    if sm1.active():
        while sm1.tx_fifo() != 0: pass
    if sm2.active():
        while sm2.tx_fifo() != 0: pass
    if sm3.active():
        while sm3.tx_fifo() != 0: pass

    sm2.active(0)
    sm3.active(0)
    sm1.active(1)

    # set column address
    _tx_command(CASET)
    _tx_data(x1 >> 8)
    _tx_data(x1 & 0xff)
    _tx_data(x2 >> 8)
    _tx_data(x2 & 0xff)

    # set row address
    _tx_command(RASET)
    _tx_data(y1 >> 8)
    _tx_data(y1 & 0xff)
    _tx_data(y2 >> 8)
    _tx_data(y2 & 0xff)

    # write RAM
    _tx_command(RAMWR)

    dc.high()

    while sm1.tx_fifo() != 0: pass


@micropython.native
def clear_display(colour = LCD_BLACK):
    """Clears the display - fed with the colour."""

    global dc, sm1, sm2, sm3

    _set_addrs(0, LCD_WIDTH - 1, 0, LCD_HEIGHT - 1)

    sm1.active(0)
    sm2.active(0)
    sm3.active(1)

    dc.high()

    # clear all pixels
    put = sm3.put
    for _ in range(LCD_WIDTH * LCD_HEIGHT / 16):
        put(colour)
        put(colour)
        put(colour)
        put(colour)
        put(colour)
        put(colour)
        put(colour)
        put(colour)


def display_on():
    """Turns the display on."""

    # screen on
    _tx_command(DISPON)


def display_off():
    """Turns the display off."""

    # clear screen
    clear_display()

    # screen off
    _tx_command(DISPOFF)


def draw_string(x, y, str, foreground, background):
    """Draws a string - fed with the coords, the string and foreground & background colours;
    returns updated x-coord."""

    for c in str:
        x = draw_char(x, y, c, foreground, background)

    return x

def draw_double_string(x, y, str, foreground, background):
    """Draws a double-size string - fed with the coords, the string and foreground & background colours;
    returns updated x-coord."""

    for c in str:
        x = draw_double_char(x, y, c, foreground, background)

    return x

def draw_triple_string(x, y, str, foreground, background):
    """Draws a triple-size string - fed with the coords, the string and foreground & background colours;
    returns updated x-coord."""

    for c in str:
        x = draw_triple_char(x, y, c, foreground, background)

    return x


@micropython.native
def draw_char(x, y, c, foreground, background):
    """Draws a character - fed with the coords, the character and foreground & background colours;
    returns updated x-coord."""

    global dc, sm1, sm2, sm3

    _set_addrs(x, x + 7, y, y + 7)

    sm1.active(0)
    sm3.active(0)
    sm2.active(1)

    dc.high()

    put = sm2.put

    if c == ' ':

        # special case
        for _ in range(8 * 8): put(background)

    else:

        i = (ord(c) - ord(' ')) << 3

        for dots in font[i : i + 8]:
            put(foreground) if dots & 0b10000000 else put(background)
            put(foreground) if dots & 0b01000000 else put(background)
            put(foreground) if dots & 0b00100000 else put(background)
            put(foreground) if dots & 0b00010000 else put(background)
            put(foreground) if dots & 0b00001000 else put(background)
            put(foreground) if dots & 0b00000100 else put(background)
            put(foreground) if dots & 0b00000010 else put(background)
            put(foreground) if dots & 0b00000001 else put(background)

    return x + 8


@micropython.native
def draw_double_char(x, y, c, foreground, background):
    """Draws a double-size character - fed with the coords, the character and foreground & background colours;
    returns updated x-coord."""

    global dc, sm1, sm2, sm3

    _set_addrs(x, x + 15, y, y + 15)

    sm1.active(0)
    sm2.active(0)
    sm3.active(1)

    dc.high()

    put = sm3.put

    if c == ' ':

        # special case
        for _ in range(16 * 16 / 2): put(background)

    else:

        i = (ord(c) - ord(' ')) << 3

        for dots in font[i : i + 8]:
            put(foreground) if dots & 0b10000000 else put(background)
            put(foreground) if dots & 0b01000000 else put(background)
            put(foreground) if dots & 0b00100000 else put(background)
            put(foreground) if dots & 0b00010000 else put(background)
            put(foreground) if dots & 0b00001000 else put(background)
            put(foreground) if dots & 0b00000100 else put(background)
            put(foreground) if dots & 0b00000010 else put(background)
            put(foreground) if dots & 0b00000001 else put(background)
            put(foreground) if dots & 0b10000000 else put(background)
            put(foreground) if dots & 0b01000000 else put(background)
            put(foreground) if dots & 0b00100000 else put(background)
            put(foreground) if dots & 0b00010000 else put(background)
            put(foreground) if dots & 0b00001000 else put(background)
            put(foreground) if dots & 0b00000100 else put(background)
            put(foreground) if dots & 0b00000010 else put(background)
            put(foreground) if dots & 0b00000001 else put(background)

    return x + 16


@micropython.native
def _tx_colour3(colour):
    global sm2
    sm2.put(colour)
    sm2.put(colour)
    sm2.put(colour)

@micropython.native
def draw_triple_char(x, y, c, foreground, background):
    """Draws a triple-size character - fed with the coords, the character and foreground & background colours;
    returns updated x-coord."""

    global dc, sm1, sm2, sm3

    _set_addrs(x, x + 23, y, y + 23)

    sm1.active(0)
    sm3.active(0)
    sm2.active(1)

    dc.high()

    tx = _tx_colour3

    if c == ' ':

        # special case
        for _ in range(24 * 24 / 3): tx(background)

    else:

        i = (ord(c) - ord(' ')) << 3

        for dots in font[i : i + 8]:
            tx(foreground) if dots & 0b10000000 else tx(background)
            tx(foreground) if dots & 0b01000000 else tx(background)
            tx(foreground) if dots & 0b00100000 else tx(background)
            tx(foreground) if dots & 0b00010000 else tx(background)
            tx(foreground) if dots & 0b00001000 else tx(background)
            tx(foreground) if dots & 0b00000100 else tx(background)
            tx(foreground) if dots & 0b00000010 else tx(background)
            tx(foreground) if dots & 0b00000001 else tx(background)
            tx(foreground) if dots & 0b10000000 else tx(background)
            tx(foreground) if dots & 0b01000000 else tx(background)
            tx(foreground) if dots & 0b00100000 else tx(background)
            tx(foreground) if dots & 0b00010000 else tx(background)
            tx(foreground) if dots & 0b00001000 else tx(background)
            tx(foreground) if dots & 0b00000100 else tx(background)
            tx(foreground) if dots & 0b00000010 else tx(background)
            tx(foreground) if dots & 0b00000001 else tx(background)
            tx(foreground) if dots & 0b10000000 else tx(background)
            tx(foreground) if dots & 0b01000000 else tx(background)
            tx(foreground) if dots & 0b00100000 else tx(background)
            tx(foreground) if dots & 0b00010000 else tx(background)
            tx(foreground) if dots & 0b00001000 else tx(background)
            tx(foreground) if dots & 0b00000100 else tx(background)
            tx(foreground) if dots & 0b00000010 else tx(background)
            tx(foreground) if dots & 0b00000001 else tx(background)

    return x + 24


# displays the complete font
def _draw_font():

    clear_display()

    draw_double_string(56, 48, " :;<=>?@", LCD_GREEN, LCD_BLACK)
    draw_double_string(40, 64, "0123456789", LCD_RED, LCD_BLACK)
    draw_double_string(0, 80, "!\"#$%&'()*+,-./", LCD_BLUE, LCD_BLACK)
    draw_double_string(8, 96, "ABCDEFGHIJKLM", LCD_CYAN, LCD_BLACK)
    draw_double_string(8, 112, "NOPQRSTUVWXYZ", LCD_MAGENTA, LCD_BLACK)
    draw_double_string(8, 128, "abcdefghijklm", LCD_WHITE, LCD_BLACK)
    draw_double_string(8, 144, "nopqrstuvwxyz", LCD_ORANGE, LCD_BLACK)
    draw_double_string(72, 160, "[\\]^_`", LCD_YELLOW, LCD_BLACK)
    draw_double_string(88, 176, "{|}~", LCD_BLUE, LCD_BLACK)


# draws a decimal number on the display, returns updated x-coord
@micropython.native
def _draw_dec(x, y, n, foreground, background, func):

    leading_zeroes = True
    for d in [10000, 1000, 100, 10, 1]:
        c = n // d
        n %= d
        if c != 0: leading_zeroes = False
        if d == 1 or not leading_zeroes:
            x = func(x, y, chr(ord('0') + c), foreground, background)

    return x

def draw_decimal(x, y, n, foreground, background):
    """Draws a decimal number - fed with the coords, the number and foreground & background colours;
    returns updated x-coord."""
    return _draw_dec(x, y, n, foreground, background, draw_char)

def draw_double_decimal(x, y, n, foreground, background):
    """Draws a double-size decimal number - fed with the coords, the number and foreground & background colours;
    returns updated x-coord."""
    return _draw_dec(x, y, n, foreground, background, draw_double_char)

def draw_triple_decimal(x, y, n, foreground, background):
    """Draws a triple-size decimal number - fed with the coords, the number and foreground & background colours;
    returns updated x-coord."""
    return _draw_dec(x, y, n, foreground, background, draw_triple_char)


@micropython.native
def draw_pixel(x, y, foreground):
    """Sets a single pixel to a colour - fed with the coords and the colour."""

    global dc, sm1, sm2, sm3

    _set_addrs(x, x + 0, y, y + 0)

    sm1.active(0)
    sm3.active(0)
    sm2.active(1)

    dc.high()

    sm2.put(foreground)


@micropython.native
def draw_quad_pixel(x, y, foreground):
    """Sets four pixels to a colour - fed with the coords and the colour."""

    global dc, sm1, sm2, sm3

    _set_addrs(x, x + 1, y, y + 1)

    sm1.active(0)
    sm2.active(0)
    sm3.active(1)

    dc.high()

    sm3.put(foreground)
    sm3.put(foreground)


@micropython.native
def draw_line(x1, y1, x2, y2, foreground):
    """Draws a line between two points - fed with the coords and the colour."""

    points = _bresenham(x1, y1, x2, y2)
    for x, y in points: draw_quad_pixel(x, y, foreground)


@micropython.native
def _bresenham(x0, y0, x1, y1):

    dx = x1 - x0
    dy = y1 - y0

    xsign = 1 if dx > 0 else -1
    ysign = 1 if dy > 0 else -1

    dx = abs(dx)
    dy = abs(dy)

    if dx > dy:
        xx, xy, yx, yy = xsign, 0, 0, ysign
    else:
        dx, dy = dy, dx
        xx, xy, yx, yy = 0, ysign, xsign, 0

    D = 2*dy - dx
    y = 0

    for x in range(dx + 1):
        yield x0 + x*xx + y*yx, y0 + x*xy + y*yy
        if D >= 0:
            y += 1
            D -= 2*dx
        D += 2*dy


@micropython.native
def draw_splash():
    """Loads and displays the splash screen."""

    global dc, sm1, sm2, sm3

    SPLASH_WIDTH = const(120)
    SPLASH_HEIGHT = const(120)

    x1 = (LCD_WIDTH - SPLASH_WIDTH * 2) // 2
    x2 = x1 + SPLASH_WIDTH * 2
    y1 = (LCD_HEIGHT - SPLASH_HEIGHT * 2) // 2
    y2 = y1 + SPLASH_HEIGHT * 2

    buffer = bytearray(SPLASH_WIDTH * 2)

    with open("splash.bin", "rb") as f:

        _set_addrs(x1, x2 - 1, y1, y2 - 1)

        sm1.active(0)
        sm2.active(0)
        sm3.active(1)

        dc.high()

        for y in range(y1, y2, 2):

            len = f.readinto(buffer)
            if len < SPLASH_WIDTH * 2: return

            for i in range(0, SPLASH_WIDTH * 2, 2 * 4):
                sm3.put((buffer[i+0] << 8) + buffer[i+1])
                sm3.put((buffer[i+2] << 8) + buffer[i+3])
                sm3.put((buffer[i+4] << 8) + buffer[i+5])
                sm3.put((buffer[i+6] << 8) + buffer[i+7])
            for i in range(0, SPLASH_WIDTH * 2, 2 * 4):
                sm3.put((buffer[i+0] << 8) + buffer[i+1])
                sm3.put((buffer[i+2] << 8) + buffer[i+3])
                sm3.put((buffer[i+4] << 8) + buffer[i+5])
                sm3.put((buffer[i+6] << 8) + buffer[i+7])


#------------------------------------------------------------------------
# initialisation
#------------------------------------------------------------------------

# configure pins
dc = Pin(DC_PIN, Pin.OUT)
cs = Pin(CS_PIN, Pin.OUT)
cs.off()
res = Pin(RES_PIN, Pin.OUT)
res.on()

sm1 = StateMachine(LCD_SM1, _tx_8, freq=SPI_SPEED, out_base=Pin(SDA_PIN), sideset_base=Pin(SCL_PIN))
sm1.active(0)

sm2 = StateMachine(LCD_SM2, _tx_16, freq=SPI_SPEED, out_base=Pin(SDA_PIN), sideset_base=Pin(SCL_PIN))
sm2.active(0)

sm3 = StateMachine(LCD_SM3, _tx_32, freq=SPI_SPEED, out_base=Pin(SDA_PIN), sideset_base=Pin(SCL_PIN))
sm3.active(0)

# reset display
res.on()
sleep(0.010)
res.off()
sleep(0.010)
res.on()
sleep(0.010)

sm2.active(0)
sm3.active(0)
sm1.active(1)

# software reset
_tx_command(SWRESET)
sleep(0.150)

_tx_command(INTER_ENABLE2)

_tx_command(0xEB)
_tx_data(0x14)

_tx_command(INTER_ENABLE1)
_tx_command(INTER_ENABLE2)

_tx_command(0xEB)
_tx_data(0x14)

_tx_command(0x84)
_tx_data(0x40)

_tx_command(0x85)
_tx_data(0xFF)

_tx_command(0x86)
_tx_data(0xFF)

_tx_command(0x87)
_tx_data(0xFF)

_tx_command(0x88)
_tx_data(0x0A)

_tx_command(0x89)
_tx_data(0x21)

_tx_command(0x8A)
_tx_data(0x00)

_tx_command(0x8B)
_tx_data(0x80)

_tx_command(0x8C)
_tx_data(0x01)

_tx_command(0x8D)
_tx_data(0x01)

_tx_command(0x8E)
_tx_data(0xFF)

_tx_command(0x8F)
_tx_data(0xFF)

_tx_command(DISPLAY_CONTROL)
_tx_data(0x00)
_tx_data(0x00)

# set memory data access control
_tx_command(MADCTL)
# left to right, top to bottom, BGR
_tx_data(MADCTL_MX | MADCTL_BGR)
sleep(0.010)

# set colour mode
_tx_command(COLMOD)
# 16-bit colour
_tx_data(0x55)
sleep(0.010)

_tx_command(0x90)
_tx_data(0x08)
_tx_data(0x08)
_tx_data(0x08)
_tx_data(0x08)

_tx_command(0xBD)
_tx_data(0x06)

_tx_command(0xBC)
_tx_data(0x00)

_tx_command(0xFF)
_tx_data(0x60)
_tx_data(0x01)
_tx_data(0x04)

_tx_command(POWER_CONTROL2)
_tx_data(0x13)
_tx_command(POWER_CONTROL3)
_tx_data(0x13)
_tx_command(POWER_CONTROL4)
_tx_data(0x22)

_tx_command(0xBE)
_tx_data(0x11)

_tx_command(0xE1)
_tx_data(0x10)
_tx_data(0x0E)

_tx_command(0xDF)
_tx_data(0x21)
_tx_data(0x0c)
_tx_data(0x02)

_tx_command(SET_GAMMA1)
_tx_data(0x45)
_tx_data(0x09)
_tx_data(0x08)
_tx_data(0x08)
_tx_data(0x26)
_tx_data(0x2A)

_tx_command(SET_GAMMA2)
_tx_data(0x43)
_tx_data(0x70)
_tx_data(0x72)
_tx_data(0x36)
_tx_data(0x37)
_tx_data(0x6F)

_tx_command(SET_GAMMA3)
_tx_data(0x45)
_tx_data(0x09)
_tx_data(0x08)
_tx_data(0x08)
_tx_data(0x26)
_tx_data(0x2A)

_tx_command(SET_GAMMA4)
_tx_data(0x43)
_tx_data(0x70)
_tx_data(0x72)
_tx_data(0x36)
_tx_data(0x37)
_tx_data(0x6F)

_tx_command(0xED)
_tx_data(0x1B)
_tx_data(0x0B)

_tx_command(0xAE)
_tx_data(0x77)

_tx_command(0xCD)
_tx_data(0x63)

_tx_command(0x70)
_tx_data(0x07)
_tx_data(0x07)
_tx_data(0x04)
_tx_data(0x0E)
_tx_data(0x0F)
_tx_data(0x09)
_tx_data(0x07)
_tx_data(0x08)
_tx_data(0x03)

_tx_command(FRAMERATE)
_tx_data(0x34)

_tx_command(0x62)
_tx_data(0x18)
_tx_data(0x0D)
_tx_data(0x71)
_tx_data(0xED)
_tx_data(0x70)
_tx_data(0x70)
_tx_data(0x18)
_tx_data(0x0F)
_tx_data(0x71)
_tx_data(0xEF)
_tx_data(0x70)
_tx_data(0x70)

_tx_command(0x63)
_tx_data(0x18)
_tx_data(0x11)
_tx_data(0x71)
_tx_data(0xF1)
_tx_data(0x70)
_tx_data(0x70)
_tx_data(0x18)
_tx_data(0x13)
_tx_data(0x71)
_tx_data(0xF3)
_tx_data(0x70)
_tx_data(0x70)

_tx_command(0x64)
_tx_data(0x28)
_tx_data(0x29)
_tx_data(0xF1)
_tx_data(0x01)
_tx_data(0xF1)
_tx_data(0x00)
_tx_data(0x07)

_tx_command(0x66)
_tx_data(0x3C)
_tx_data(0x00)
_tx_data(0xCD)
_tx_data(0x67)
_tx_data(0x45)
_tx_data(0x45)
_tx_data(0x10)
_tx_data(0x00)
_tx_data(0x00)
_tx_data(0x00)

_tx_command(0x67)
_tx_data(0x00)
_tx_data(0x3C)
_tx_data(0x00)
_tx_data(0x00)
_tx_data(0x00)
_tx_data(0x01)
_tx_data(0x54)
_tx_data(0x10)
_tx_data(0x32)
_tx_data(0x98)

_tx_command(0x74)
_tx_data(0x10)
_tx_data(0x85)
_tx_data(0x80)
_tx_data(0x00)
_tx_data(0x00)
_tx_data(0x4E)
_tx_data(0x00)

_tx_command(0x98)
_tx_data(0x3e)
_tx_data(0x07)

_tx_command(TEON)
_tx_data(0x00)

clear_display()

# display inversion on
_tx_command(INVON)
sleep(0.010)

# exit sleep mode
_tx_command(SLPOUT)
sleep(0.500)

# screen on
_tx_command(DISPON)
sleep(0.500)

# normal display on
_tx_command(NORON)
sleep(0.010)

# splash screen
draw_splash()
sleep(2)

# credits
clear_display()
draw_double_string(40, 60, "PERPLEXITY", LCD_RED, LCD_BLACK)
draw_double_string(40, 92, "Written by", LCD_WHITE, LCD_BLACK)
draw_double_string(16, 112, "James Hutchby", LCD_WHITE, LCD_BLACK)
draw_double_string(8, 140, "www.madlab.org", LCD_BLUE, LCD_BLACK)
draw_double_string(32, 160, "@clubmadlab", LCD_BLUE, LCD_BLACK)


#------------------------------------------------------------------------
# module test
#------------------------------------------------------------------------

# _draw_font()
