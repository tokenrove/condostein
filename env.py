import logging
import pygame

import config

vbuffer = None
display_sface = None
clock = None
# FX
_overlay = None
_overlay_p = False
# controller aspect
quit_raised = False
buttons = ['UP', 'DOWN', 'LEFT', 'RIGHT', 'FIRE', 'ESCAPE', 'DEBUG_TOGGLE']
bindings = config.KEY_BINDINGS
pressed = dict().fromkeys(buttons, False)
tapped = dict().fromkeys(buttons, False)
joysticks = []

def init(options):
    pygame.init()
    # clock for frame timing
    global clock
    clock = pygame.time.Clock()
    # init display
    dim = config.VIRTUAL_DIMENSIONS
    if config.SCALE != 1: dim = map(lambda x:config.SCALE*x, dim)
    pygame.display.set_mode(dim, 0 if 'fullscreen' not in options else pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    global vbuffer, display_sface, _overlay
    vbuffer = display_sface = pygame.display.get_surface()
    if config.SCALE != 1:
        vbuffer = pygame.Surface(config.VIRTUAL_DIMENSIONS, 0, vbuffer)
    _overlay = display_sface.copy()
    # init joysticks
    if pygame.joystick.get_count() > 0:
        global joysticks
        joysticks = [pygame.joystick.Joystick(i) for i in xrange(pygame.joystick.get_count())]
        for j in joysticks:
            j.init()
            logging.debug('env: Initialized joystick "%s" (%d)' % (j.get_name(), j.get_id()))

def _process_events():
    #timestamp = pygame.time.get_ticks()
    for x in tapped.keys(): tapped[x] = False
    for event in pygame.event.get():
        if event.type == pygame.locals.QUIT:
            global quit_raised
            quit_raised = pressed['ESCAPE'] = True
            break
        elif event.type == pygame.JOYAXISMOTION:
            dir = ('UP','DOWN') if (event.axis&1) == 0 else ('LEFT','RIGHT')
            if event.value > config.JOYSTICK_EPSILON:
                pressed[dir[1]] = tapped[dir[1]] = True
                pressed[dir[0]] = False
            elif event.value < -config.JOYSTICK_EPSILON:
                pressed[dir[0]] = tapped[dir[0]] = True
                pressed[dir[1]] = False
            else:
                pressed[dir[0]] = pressed[dir[1]] = False
            continue
        elif event.type not in (pygame.locals.KEYDOWN, pygame.locals.KEYUP,
                            pygame.locals.JOYBUTTONDOWN, pygame.locals.JOYBUTTONUP):
            continue
        state = event.type in (pygame.locals.KEYDOWN, pygame.locals.JOYBUTTONDOWN)
        value = event.key if event.type in (pygame.locals.KEYDOWN, pygame.locals.KEYUP) else event.button
        # _key_state[event.key] = timestamp if pressed else 0
        if value in bindings:
            bind = bindings[value]
            if state: tapped[bind] = state
            pressed[bind] = state

def fade(amount):
    global _overlay_p
    if amount < 1.0-config.EPSILON:
        _overlay.fill(0)
        _overlay.set_alpha(255 * (1.0 - amount))
        _overlay_p = True
    else:
        _overlay_p = False

def update():
    if config.SCALE != 1:
        pygame.transform.scale(vbuffer, map(lambda x:config.SCALE*x, config.VIRTUAL_DIMENSIONS),
                               display_sface)
    if _overlay_p: display_sface.blit(_overlay, (0,0))
    pygame.display.flip()
    global vbuffer_valid
    vbuffer_valid = True
    _process_events()
    clock.tick(config.FRAMES_PER_SECOND)
    return clock.get_time() / 1000.0

def debug_rect(rect, color):
    pygame.draw.rect(vbuffer, color, rect, 1)

