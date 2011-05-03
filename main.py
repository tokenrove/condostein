
import sys, os, math

import config, env, slabcache, fluff, transition, font, sprite, tilemap
from util import *

def sink(v, a):
    return 0 if abs(v) <= abs(a) else (v-math.copysign(a, v))
def damp(v, factor):
    return sink(v, v*factor)

class Actor(sprite.Sprite):
    def __init__(self, archetype=None, spawn_pt=(0,0), parent=None, **kwds):
        sprite.Sprite.__init__(self, slab=slabcache.load(archetype['slab']),
                               position=spawn_pt,
                               animations=archetype['animations'], **kwds)
        self.archetype = archetype
        (self.vx,self.vy) = (0,0)
        self.parent = parent
        parent.smirch(self.rect)

    def invalidate_rect(self):
        self.parent.smirch(self.rect)

    def act(self, delta_t):
        sprite.Sprite.update(self, delta_t)

    def update_motion(self, delta_t):
        (self.x,self.y) = (self.x+self.vx,self.y+self.vy)
        self.vx = damp(self.vx, config.DAMPING)
        self.vy = damp(self.vy, config.DAMPING)


    def border_collide(self, facing):
        logging.debug('collided with %s border' % facing)

class HumanoidActor(Actor):
    def act(self, delta_t):
        for (button,facing) in (('UP',Facing.NORTH),('DOWN',Facing.SOUTH),
                               ('LEFT',Facing.EAST),('RIGHT',Facing.WEST)):
            if env.tapped[button]:
                self.facing = facing
                self.animation(Facing.to_anim_name(facing))
                break
        for (button,delta) in (('UP',(0,-1)),('DOWN',(0,1)),('LEFT',(-1,0)),('RIGHT',(1,0))):
            if env.pressed[button]:
                delta = map(lambda x: delta_t * self.archetype['walking speed'] * x * (self.archetype['creep modifier'] if env.tapped[button] else 1), delta)
                (self.vx,self.vy) = (self.vx+delta[0],self.vy+delta[1])
                self.rect_valid = False
        Actor.act(self, delta_t)

archetypes = {
    'humanoid':
        {'class':HumanoidActor,
         'slab':'humanoid.png',
         'walking speed':50,    # pixels/second
         'creep modifier':0.5,
         'animations':{'face north': [(0,Rect(0,0,27,13))],
                       'face south': [(0,Rect(27,0,27,13))],
                       'face east': [(0,Rect(54,0,13,27))],
                       'face west': [(0,Rect(67,0,13,27))],},
         },
    'robot':
        {'class':Actor,
         'slab':'robot.png',
         'walking speed':15,    # pixels/second
         'animations':{'face south': [(0,Rect(0,0,25,22))],
                       'face north': [(0,Rect(25,0,25,22))],
                       'face east': [(0,Rect(50,0,22,25))],
                       'face west': [(0,Rect(72,0,22,25))],},
         },
    'shot':
        {'class':Actor,
         'slab':'shot.png',
         'animations':{'default': [(.1,Rect(0,0,6,6)),
                                   (.05,Rect(6,0,6,6)),
                                   (.05,Rect(12,0,6,6))]},},
}

level = [{'map':
              [0,1,1,1,1,1,1,1,1,1,1,1,1,8,1,4,4,4,4,2,
               3,4,4,4,4,4,4,4,4,4,4,4,4,1,4,4,4,4,4,3,
               3,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,3,
               3,4,4,4,4,4,4,8,1,1,1,1,1,4,4,4,4,1,1,2,
               3,4,4,4,4,4,4,3,4,4,4,4,4,3,4,4,4,4,4,3,
               3,4,4,4,4,4,4,3,4,4,4,4,4,3,4,4,4,4,4,3,
               0,1,4,4,4,4,4,3,4,4,4,4,4,3,4,4,4,4,4,3,
               3,4,4,4,4,4,4,3,4,4,4,4,4,3,4,4,4,4,4,3,
               3,4,4,4,4,4,4,3,4,4,4,4,4,3,4,4,4,4,4,3,
               3,4,4,4,4,4,4,3,4,4,4,4,4,3,4,4,4,4,4,3,
               0,1,1,1,1,1,1,8,1,1,1,1,1,8,1,1,1,1,1,2,
               3,4,4,4,4,4,4,3,4,4,4,4,4,3,4,4,4,4,4,3,
               5,6,6,6,6,6,6,7,6,6,6,6,6,7,6,6,6,6,6,7,],
          'dim': (20,13),
          'tile properties': {4: set([tilemap.PASSABLE]) },
          'slab': 'basic.png'}]

class Room:
    #triggers

    def __init__(self, **kwds):
        self.dirt = []
        self.actors = []
        # NOTE: no alpha since no layers, presently
        self.tilemap = tilemap.SimpleTilemap(slabcache.load(level[0]['slab']), level[0]['map'], level[0]['dim'])
        self.dirt.append(Rect(0,0,320,240))

    def spawn(self, archetype, position):
        self.actors.append(archetypes[archetype]['class'](archetype=archetypes[archetype],
                                                          spawn_pt=position,
                                                          parent=self))

    # We could merge common subrectangles here, but it's probably not
    # necessary.  If profiling shows it's costly, we can change the
    # data structure.  At least checking to see if the same rectangle
    # is already there might help in some cases.
    def smirch(self, rect):
        self.dirt.append(rect)

    # redraw that flags an area as dirty: when an actor is placed or
    # moved, its _old_ position is flagged as dirty; redraw then draws
    # only the background areas marked dirty, and then draws the sprites.
    # animation marks an area dirty, so does moving.
    def sweep(self):
        for d in self.dirt: self.tilemap.draw((0,0), d)
        self.dirt = []

    def update(self, delta_t):
        # physics and collision
        for actor in self.actors:
            # world collision, if applicable
            self.check_border_collision(actor)
            self.check_tile_collision(actor)
            # collision with groups, if applicable
            self.check_actor_collision(actor)
            actor.update_motion(delta_t)
            actor.act(delta_t)
        self.sweep()
        for actor in self.actors: actor.draw()

    def check_border_collision(self, actor):
        if actor.x < 0 and actor.vx < 0:
            actor.border_collide(Facing.EAST)
        elif actor.x > self.tilemap.w*self.tilemap.tile_dim and actor.vx > 0:
            actor.border_collide(Facing.WEST)
        if actor.y < 0 and actor.vy < 0:
            actor.border_collide(Facing.NORTH)
        elif actor.y > self.tilemap.h*self.tilemap.tile_dim and actor.vy > 0:
            actor.border_collide(Facing.SOUTH)

    def check_tile_collision(self, actor):
        pass

    def check_actor_collision(self, actor):
        pass

# concepts of game loop, rooms, actors

# states:
#   SPLASH -> TITLE
#   TITLE -> { EXIT, NEW_GAME, HIGHSCORE, DEMO }
#   NEW_GAME -> GAME(first level)
#   GAME(level) -> { GAME(next level), HIGHSCORE, TITLE, ENDGAME }
#   ENDGAME -> { HIGHSCORE }
#   HIGHSCORE -> { TITLE }


class GameState(State):
    def __init__(self, room=None, **kwds):
        self.score = 0
        # load a room
        self.room = Room()
        self.font = font.TroglodyteFont('megafont.png')
        # populate the room
        self.room.spawn('humanoid', (50,50))
        self.room.spawn('shot', (50,50))
        # debug
        self.debug_toggle = False

    def update(self, delta_t):
        self.room.update(delta_t)
        self.font.blit('%08d' % self.score, (10,220))
        if env.tapped['DEBUG_TOGGLE']:
            self.debug_toggle = not self.debug_toggle
        if self.debug_toggle:
            for actor in self.room.actors:
                env.debug_rect(actor.rect, 0xffff00)
        if env.tapped['ESCAPE']: return TitleState()
        return self

class TitleState(State):
    def __init__(self, **kwds):
        State.__init__(self, **kwds)
        # XXX title state can be a singleton; cache resources and so on after the first time
        self.title = slabcache.load(config.TITLE_IMAGE)
        self.accumulated_t = 0
        self.font = font.TroglodyteFont('megafont.png')
        self.selected = 0
        self.menu = [('START', self.start_new_game),
                     ('HIGHSCORE', lambda:None), ('CONFIG', lambda:None), ('QUIT', lambda:None)]

    def draw_crude_menu(self):
        #pointers = ['--->','_-->','__->','___>','-__>','--_>',]
        pointers = ["<:   >","< :  >","<  : >","<   :>","<  : >","< :  >"]
        for (i,entry) in enumerate(self.menu):
            self.font.blit(entry[0], (200, 200+10*i))
            if i == self.selected:
                self.font.blit(pointers[int(self.accumulated_t/0.1%len(pointers))], (145,200+10*i))

    def start_new_game(self):
        return transition.FadeOutIn(out_from=self, in_to=GameState())

    def update(self, delta_t):
        self.accumulated_t += delta_t
        env.vbuffer.blit(self.title, (0,0))

        self.draw_crude_menu()
        if env.tapped['ESCAPE']: return None
        if env.tapped['UP']: self.selected = (self.selected-1) % len(self.menu)
        if env.tapped['DOWN']: self.selected = (self.selected+1) % len(self.menu)
        if env.tapped['FIRE']: return self.menu[self.selected][1]()

        if any(env.tapped.values()):
            self.accumulated_t = 0
        if self.accumulated_t > config.IDLE_TIME_BEFORE_DEMO:
            return transition.FadeOutIn(out_from=self, in_to=DemoState())
        return self

class DemoState(State):
    def __init__(self, **kwds):
        State.__init__(self, **kwds)

import logging
def main():
    if '-debug' in sys.argv:
        logging.getLogger().setLevel(logging.DEBUG)
    env.init()
    state = TitleState()
    if not '-fast' in sys.argv:
        state = transition.FadeInOut(hold_duration=2, atop=fluff.SplashState(),
                                     after=transition.Fade(atop=state, after=state, duration=2.0, start=0.0, end=1.0))

    while state and not env.quit_raised:
        delta_t = env.update()
        if delta_t >= config.TIMING_EPSILON:
            state = state.update(delta_t)
if __name__ == '__main__': main()
