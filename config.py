"""
This module is for configuration of the game.  Presently, nothing is
configurable after delivery, so this file should only contain
constants.  In the future, these may be loaded from a configuration
file.
"""

VIRTUAL_DIMENSIONS = (320,240)
SCALE = 2

FRAMES_PER_SECOND = 50
EPSILON = 0.0000001
TIMING_EPSILON = 0.00001
JOYSTICK_EPSILON = 0.01

SPLASH_IMAGE = 'splash.png'
TITLE_IMAGE = 'title.png'
IDLE_TIME_BEFORE_DEMO = 10
ENDGAME_IMAGE = 'splash.png'
END_GAME_DISPLAY_TIME = 10

from pygame.locals import *
KEY_BINDINGS = {
    0: 'FIRE',
    1: 'FIRE',
    2: 'FIRE',
    3: 'FIRE',

    K_UP: 'UP',
    K_DOWN: 'DOWN',
    K_LEFT: 'LEFT',
    K_RIGHT: 'RIGHT',
    K_ESCAPE: 'ESCAPE',
    K_LSHIFT: 'FIRE',
    K_z: 'FIRE',
    K_RETURN: 'FIRE',

    K_BACKQUOTE: 'DEBUG_TOGGLE',
}

#### PHYSICS

DAMPING = 1.0
