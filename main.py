
import sys, os, math, random

import config, env, slabcache, fluff, transition, font, sprite, tilemap
from util import *

class Actor(sprite.Sprite):
    (HARMFUL, PREY, HUNTER) = range(3)

    def __init__(self, archetype=None, spawn_pt=(0,0), parent=None, velocity=(0,0), **kwds):
        sprite.Sprite.__init__(self, slab=slabcache.load(archetype['slab']),
                               position=spawn_pt,
                               animations=archetype['animations'], **kwds)
        self.archetype = archetype
        (self.vx,self.vy) = velocity
        self.parent = parent
        parent.smirch(self.rect)

    def die(self): self.parent.reap(self)

    def invalidate_rect(self):
        self.parent.smirch(self.rect)

    def act(self, delta_t):
        sprite.Sprite.update(self, delta_t)

    def update_motion(self, delta_t):
        (self.x,self.y) = (self.x+self.vx,self.y+self.vy)
        self.vx = damp(self.vx, config.DAMPING)
        self.vy = damp(self.vy, config.DAMPING)

    def border_collide(self, facing): pass
    def tile_collide(self, position, properties): pass
    def collide(self, other): return False

class HumanoidActor(Actor):
    def __init__(self, **kwds):
        Actor.__init__(self, **kwds)
        self.facing = Facing.NORTH
        self.animation(Facing.to_anim_name(self.facing))

    def border_collide(self, facing):
        self.parent.humanoid_escapes(facing)

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
        if env.tapped['FIRE']:
            vector = map(lambda x:x*self.archetype['shot speed'], ((0,-1),(0,1),(-1,0),(1,0))[self.facing])
            spawn = ((self.x,self.rect.top),(self.x,self.rect.bottom),(self.rect.left,self.y),(self.rect.right,self.y))[self.facing]
            self.parent.spawn('shot', spawn, vector=vector, owner=self)
        Actor.act(self, delta_t)

class ShotActor(Actor):
    def __init__(self, vector=(-1,0), owner=None, **kwds):
        Actor.__init__(self, **kwds)
        (self.vector,self.owner,self.disown_delay) = (vector,owner,self.archetype['disown delay'])

    def act(self, delta_t):
        (self.vx,self.vy) = map(lambda x:x*delta_t, self.vector)
        self.disown_delay -= delta_t
        if self.disown_delay < 0: self.owner = None
        Actor.act(self, delta_t)

    def border_collide(self, facing): self.die()
    def tile_collide(self, position, properties): self.die()

    def collide(self, other):
        if other is self.owner: return False
        self.die()
        return True

class RobotActor(Actor):
    def roam(self, delta_t):
        (self.vx,self.vy) = map(lambda x:x*self.archetype['walking speed']*delta_t,
                                ((0,-1),(0,1),(-1,0),(0,1))[self.facing])

    def border_collide(self, facing):
        self.facing = random.choice(Facing.directions)
        self.animation(Facing.to_anim_name(self.facing))

    def tile_collide(self, position, properties):
        self.facing = random.choice(Facing.directions)
        self.animation(Facing.to_anim_name(self.facing))

    def hunt(self, delta_t): pass
    def dying(self, delta_t):
        self.die()

    def collide(self, other):
        if self.act_fn is self.dying: return False
        p = other.archetype['properties']
        if Actor.HARMFUL in p:
            self.act_fn = self.dying
            self.parent.score_points('killed robot')
            return True

    def __init__(self, **kwds):
        Actor.__init__(self, **kwds)
        self.act_fn = self.roam
        self.facing = random.choice(Facing.directions)
        self.animation(Facing.to_anim_name(self.facing))

    def act(self, delta_t):
        self.act_fn(delta_t)
        self.rect_valid = False
        Actor.act(self, delta_t)

archetypes = {
    'humanoid':
        {'class':HumanoidActor,
         'properties':set([Actor.PREY]),
         'slab':'humanoid.png',
         'walking speed':50,    # pixels/second
         'creep modifier':0.5,
         'shot speed':60,       # pixels/second
         'animations':{'face north': [(0,Rect(0,0,27,13))],
                       'face south': [(0,Rect(27,0,27,13))],
                       'face east': [(0,Rect(54,0,13,27))],
                       'face west': [(0,Rect(67,0,13,27))],},
         },
    'robot':
        {'class':RobotActor,
         'properties':set([Actor.HUNTER, Actor.HARMFUL]),
         'slab':'robot.png',
         'walking speed':50,    # pixels/second
         'shot speed':45,       # pixels/second
         'animations':{'face south': [(0,Rect(0,0,25,22))],
                       'face north': [(0,Rect(25,0,25,22))],
                       'face east': [(0,Rect(50,0,22,25))],
                       'face west': [(0,Rect(72,0,22,25))],},
         },
    'shot':
        {'class':ShotActor,
         'properties':set([Actor.HARMFUL]),
         'slab':'shot.png',
         'disown delay':2,
         'animations':{'default': [(.1,Rect(0,0,6,6)),
                                   (.05,Rect(6,0,6,6)),
                                   (.05,Rect(12,0,6,6))]},},
}

class Room:
    def __init__(self, parent=None, level=None, **kwds):
        (self.dirt, self.actors, self.condemned) = ([],[],set())
        (self.parent, self.level) = (parent,level)
        # NOTE: no alpha since no layers, presently
        self.tilemap = tilemap.SimpleTilemap(slabcache.load(level['slab']), level['map'], level['dim'])
        self.dirt.append(Rect(0,0,320,240))
        for (archetype,position) in level['actors']: self.spawn(archetype, position)

    def spawn(self, archetype, position, **kwds):
        self.actors.append(archetypes[archetype]['class'](archetype=archetypes[archetype],
                                                          spawn_pt=position,
                                                          parent=self,
                                                          **kwds))

    def reap(self, actor):
        self.dirt.append(actor.rect)
        self.condemned.add(actor)

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
        map(lambda actor: self.dirt.append(actor.rect), self.condemned)
        map(self.actors.remove, self.condemned)
        self.condemned.clear()

    def check_border_collision(self, actor):
        if actor.rect.left <= 0 and actor.vx <= 0:
            (actor.vx, actor.x) = (0, actor.rect.w/2)
            actor.border_collide(Facing.EAST)
        elif actor.rect.right > self.tilemap.w*self.tilemap.tile_dim and actor.vx >= 0:
            (actor.vx, actor.x) = (0, self.tilemap.w*self.tilemap.tile_dim-actor.rect.w/2)
            actor.border_collide(Facing.WEST)
        if actor.rect.top <= 0 and actor.vy <= 0:
            (actor.vy, actor.y) = (0, actor.rect.h/2)
            actor.border_collide(Facing.NORTH)
        elif actor.rect.bottom > self.tilemap.h*self.tilemap.tile_dim and actor.vy >= 0:
            (actor.vy, actor.y) = (0, self.tilemap.h*self.tilemap.tile_dim-actor.rect.h/2)
            actor.border_collide(Facing.SOUTH)

    def check_tile_collision(self, actor):
        region = actor.rect
        tshift = self.tilemap.tile_dim_pot
        tmask = ~((1<<self.tilemap.tile_dim_pot)-1)
        # only draw tiles in region offset by camera
        for y in xrange(region.top&tmask, self.tilemap.tile_dim+(region.bottom&tmask), self.tilemap.tile_dim):
            for x in xrange(region.left&tmask, self.tilemap.tile_dim+(region.right&tmask), self.tilemap.tile_dim):
                props = self.level['tile properties'].get(self.tilemap.map[(x>>tshift)+(y>>tshift)*self.tilemap.w])
                # compute vector from center of actor to center of tile
                center = (x+self.tilemap.tile_dim/2, y+self.tilemap.tile_dim/2)
                delta = (center[0]-actor.x, center[1]-actor.y)
                # only flag collision if velocity differs (note this
                # check should not apply to special properties, only
                # passable)
                if props is None or tilemap.PASSABLE not in props:
                    if signum(delta[0])*signum(actor.vx) == 1: actor.vx = 0
                    if signum(delta[1])*signum(actor.vy) == 1: actor.vy = 0
                    actor.tile_collide((x,y), props)

    def check_actor_collision(self, actor):
        for other in self.actors:
            if other == actor: continue
            if actor.rect.colliderect(other.rect):
                if actor.collide(other):
                    if signum(actor.vx)*signum(other.vx) == -1: actor.vx = 0
                    if signum(actor.vy)*signum(other.vy) == -1: actor.vy = 0

    def humanoid_escapes(self, facing):
        self.parent.humanoid_escapes(facing)

    def score_points(self, achievement):
        self.parent.score_points(achievement)

# concepts of game loop, rooms, actors

# states:
#   SPLASH -> TITLE
#   TITLE -> { EXIT, NEW_GAME, HIGHSCORE, DEMO }
#   NEW_GAME -> GAME(first level)
#   GAME(level) -> { GAME(next level), HIGHSCORE, TITLE, ENDGAME }
#   ENDGAME -> { HIGHSCORE }
#   HIGHSCORE -> { TITLE }


levels = [{'map':
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
          'slab': 'basic.png',
          'actors': [('humanoid', (50,50)),('robot', (250,50)),('robot', (38,140))]}]

class PlayerState():
    def __init__(self):
        self.score = 0

class EndGameState(State):
    def __init__(self, player_state=None, **kwds):
        State.__init__(self, **kwds)
        self.player = player_state
        # XXX title state can be a singleton; cache resources and so on after the first time
        self.bg = slabcache.load(config.ENDGAME_IMAGE)
        self.font = font.TroglodyteFont('megafont.png')
        self.accumulated_t = 0

    def update(self, delta_t):
        self.accumulated_t += delta_t
        env.vbuffer.blit(self.bg, (0,0))
        self.font.blit('Thanks for playing!', (50,50))
        self.font.blit('Final score: %d' % self.player.score, (50,60))
        if any(env.tapped.values()) or self.accumulated_t > config.END_GAME_DISPLAY_TIME:
            return transition.FadeOutIn(out_from=self, in_to=TitleState())
        return self

class GameState(State):
    def __init__(self, level_number=1, player_state=None, **kwds):
        self.player = player_state or PlayerState()
        self.current_level = level_number-1
        # load a room
        self.room = Room(parent=self, level=levels[self.current_level])
        self.font = font.TroglodyteFont('megafont.png')
        # debug
        self.debug_toggle = False
        (self.paused,self.humanoid_escaped) = (False,False)

    def humanoid_escapes(self, border):
        logging.debug('Escaped via border %s' % border)
        if self.current_level+1 < len(levels):
            state = GameState(level_number = self.current_level+1, player_state = self.player)
        else:
            state = EndGameState(player_state = self.player)
        (self.paused,self.humanoid_escaped) = (True,True)
        self.next_state = transition.FadeOutIn(out_from=self, in_to=state)

    def score_points(self, achievement):
        points = {'killed robot':100,}[achievement]
        logging.debug('scored %s points for %s' % (points, achievement))
        self.player.score += points

    def update(self, delta_t):
        if not self.paused:
            self.room.update(delta_t)
        env.vbuffer.fill(0,(10,220,100,20))
        self.font.blit('%08d' % self.player.score, (10,220))
        if env.tapped['DEBUG_TOGGLE']:
            self.debug_toggle = not self.debug_toggle
        if self.debug_toggle:
            for actor in self.room.actors:
                env.debug_rect(actor.rect, 0xffff00)
        if env.tapped['ESCAPE']: return TitleState()
        if self.humanoid_escaped:
            self.humanoid_escaped = False
            return self.next_state
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
        return transition.FadeOutIn(out_from=self, in_to=GameState(level_number=1))

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
    random.seed()
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
