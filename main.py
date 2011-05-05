
import sys, os, math, random, operator

import config, env, slabcache, fluff, transition, font, sprite, tilemap
from util import *

import actor

class Room:
    def __init__(self, parent=None, level=None, **kwds):
        (self.dirt, self.actors, self.condemned) = ([],[],set())
        (self.parent, self.level) = (parent,level)
        # NOTE: no alpha since no layers, presently
        self.tilemap = tilemap.SimpleTilemap(slabcache.load(level['slab']), level['map'], level['dim'])
        self.smirch(env.vbuffer.get_rect())
        for (archetype,position) in level['actors']: self.spawn(archetype, position)

    def spawn(self, archetype, position, **kwds):
        self.actors.append(actor.archetypes[archetype]['class'](archetype=actor.archetypes[archetype],
                                                                spawn_pt=position,
                                                                parent=self,
                                                                **kwds))

    def reap(self, actor):
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
            actor.update_motion(delta_t)
            actor.act(delta_t)
            # world collision, if applicable
            self.check_border_collision(actor)
            self.check_tile_collision(actor)
        # collision with groups, if applicable
        self.check_actor_collisions()
        self.sweep()
        for actor in self.actors: actor.draw()
        for marked in self.condemned:
            self.smirch(marked.rect)
            self.actors.remove(marked)
        self.condemned.clear()

    def check_border_collision(self, actor):
        if actor.rect.left <= 0 and actor.velocity[0] <= 0:
            (actor.velocity[0], actor.x) = (0, actor.rect.w/2)
            actor.border_collide(Facing.EAST)
        elif actor.rect.right > self.tilemap.w*self.tilemap.tile_dim and actor.velocity[0] >= 0:
            (actor.velocity[0], actor.x) = (0, self.tilemap.w*self.tilemap.tile_dim-actor.rect.w/2)
            actor.border_collide(Facing.WEST)
        if actor.rect.top <= 0 and actor.velocity[1] <= 0:
            (actor.velocity[1], actor.y) = (0, actor.rect.h/2)
            actor.border_collide(Facing.NORTH)
        elif actor.rect.bottom > self.tilemap.h*self.tilemap.tile_dim and actor.velocity[1] >= 0:
            (actor.velocity[1], actor.y) = (0, self.tilemap.h*self.tilemap.tile_dim-actor.rect.h/2)
            actor.border_collide(Facing.SOUTH)

    def check_tile_collision(self, actor):
        region = actor.collision_rect.move(actor.rect.left, actor.rect.top)
        tile = Rect(0,0,self.tilemap.tile_dim,self.tilemap.tile_dim)
        tshift = self.tilemap.tile_dim_pot
        tmask = ~((1<<self.tilemap.tile_dim_pot)-1)
        # only draw tiles in region offset by camera
        for y in xrange(region.top&tmask, self.tilemap.tile_dim+(region.bottom&tmask), self.tilemap.tile_dim):
            if (y>>tshift) not in range(self.tilemap.h): break
            for x in xrange(region.left&tmask, self.tilemap.tile_dim+(region.right&tmask), self.tilemap.tile_dim):
                if (x>>tshift) not in range(self.tilemap.w): break
                tile.topleft = (x,y)
                if not region.colliderect(tile): break
                props = self.level['tile properties'].get(self.tilemap.map[(x>>tshift)+(y>>tshift)*self.tilemap.w])
                # compute vector from center of actor to center of tile
                delta = map(operator.sub, tile.center, region.center)
                # only flag collision if velocity differs (note this
                # check should not apply to special properties, only
                # passable)
                if props is None or tilemap.PASSABLE not in props:
                    (vx,vy) = actor.velocity
                    if abs(delta[0]) > abs(delta[1]): # horizontal
                        if delta[0] > 0:
                            actor.rect.right = x
                        else:
                            actor.rect.left = x+self.tilemap.tile_dim
                        actor.position = actor.rect.center
                        vx = 0
                    if abs(delta[1]) > abs(delta[0]): # vertical
                        if delta[1] > 0:
                            actor.rect.bottom = y
                        else:
                            actor.rect.top = y+self.tilemap.tile_dim-actor.collision_rect.top
                        actor.position = actor.rect.center
                        vy = 0
                    actor.velocity = (vx,vy)
                    actor.tile_collide((x,y), props)

    def check_actor_collisions(self):
        for actor in self.actors:
            for other in self.actors:
                if other is actor: continue
                (a,b) = (actor.collision_rect.move(actor.rect.topleft),
                         other.collision_rect.move(other.rect.topleft))
                if a.colliderect(b):
                    if actor.collide(other):
                        if signum(actor.velocity[0])*signum(other.velocity[0]) != 1:
                            actor.velocity = (0, actor.velocity[1])
                        if signum(actor.velocity[1])*signum(other.velocity[1]) != 1:
                            actor.velocity = (actor.velocity[0], 0)

    def humanoid_escapes(self, facing):
        self.parent.humanoid_escapes(facing)

    def humanoid_has_died(self):
        self.parent.humanoid_has_died()
        self.spawn(*[(x,pos) for (x,pos) in self.level['actors'] if x == 'humanoid'][0])

    def score_points(self, achievement):
        self.parent.score_points(achievement)

levels = [{'map':
              [0,2,2,2,2,2,2,2,2,2,2,2,2,8,2,1,1,1,1,2,
               4,3,3,3,3,3,3,3,3,3,3,3,3,2,3,1,1,1,1,4,
               4,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,4,
               4,1,1,1,1,1,1,8,2,2,2,2,2,1,1,1,1,2,2,2,
               4,1,1,1,1,1,1,4,3,3,3,3,3,4,1,1,1,3,3,4,
               4,1,1,1,1,1,1,4,1,1,1,1,1,4,1,1,1,1,1,4,
               0,2,1,1,1,1,1,4,1,1,1,1,1,4,1,1,1,1,1,4,
               4,3,1,1,1,1,1,4,1,1,1,1,1,4,1,1,1,1,1,4,
               4,1,1,1,1,1,1,4,1,1,1,1,1,4,1,1,1,1,1,4,
               4,1,1,1,1,1,1,4,1,1,1,1,1,4,1,1,1,1,1,4,
               0,1,1,1,1,1,1,8,0,0,0,0,0,8,0,0,0,0,0,2,
               4,1,1,1,1,1,1,4,8,8,8,8,8,4,8,8,8,9,8,4,
               5,6,6,6,6,6,6,7,6,6,6,6,6,7,6,6,6,6,6,7,],
          'dim': (20,13),
          'tile properties': {0: set([tilemap.PASSABLE]), 1: set([tilemap.PASSABLE]),
                              8: set([tilemap.PASSABLE]), 9: set([tilemap.PASSABLE]),},
          'slab': 'neutopia-rip-2.png',
          'actors': [('humanoid', (50,50)),('robot', (250,50)),('robot', (38,140))]}]

class PlayerState():
    def __init__(self):
        self.score = 0
        self.lives = config.INITIAL_LIVES

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
        (self.paused,self.transition_p) = (False,False)

    def humanoid_has_died(self):
        logging.debug('Humanoid has died.')
        self.player.lives -= 1
        if self.player.lives < 1:
            (self.paused,self.transition_p,self.next_state) = (True,True,transition.FadeOutIn(out_from=self, in_to=TitleState()))

    def humanoid_escapes(self, border):
        logging.debug('Escaped via border %s' % border)
        if self.current_level+1 < len(levels):
            state = GameState(level_number = self.current_level+1, player_state = self.player)
        else:
            state = EndGameState(player_state = self.player)
        (self.paused,self.transition_p,self.next_state) = (True,True,transition.FadeOutIn(out_from=self, in_to=state))

    def score_points(self, achievement):
        points = {'killed robot':100,}[achievement]
        logging.debug('scored %s points for %s' % (points, achievement))
        self.player.score += points

    def update(self, delta_t):
        if not self.paused:
            self.room.update(delta_t)
        env.vbuffer.fill(0,(0,208,320,32))
        self.font.blit('%08d' % self.player.score, (10,220))
        self.font.blit('Level %s' % (1+self.current_level), (10,228))
        self.font.blit('Lives: %s' % ('*' * self.player.lives), (200,220))
        if env.tapped['DEBUG_TOGGLE']:
            self.debug_toggle = not self.debug_toggle
        if self.debug_toggle:
            for actor in self.room.actors:
                env.debug_rect(actor.rect, 0xffff00)
                env.debug_rect(actor.collision_rect.move(actor.rect.left, actor.rect.top), 0xff0000)
        if env.tapped['ESCAPE']: return TitleState()
        if self.transition_p:
            self.transition_p = False
            return self.next_state
        return self

class TitleState(State):
    def __init__(self, **kwds):
        State.__init__(self, **kwds)
        # XXX title state can be a singleton; cache resources and so on after the first time
        self.title = slabcache.load(config.TITLE_IMAGE)
        (self.accumulated_t, self.paused) = (0, False)
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
        if self.paused: return self
        if env.tapped['ESCAPE']: return None
        if env.tapped['UP']: self.selected = (self.selected-1) % len(self.menu)
        if env.tapped['DOWN']: self.selected = (self.selected+1) % len(self.menu)
        if env.tapped['FIRE']: return self.menu[self.selected][1]()

        if any(env.tapped.values()):
            self.accumulated_t = 0
        if self.accumulated_t > config.IDLE_TIME_BEFORE_DEMO:
            self.paused = True
            return transition.FadeOutIn(out_from=self, in_to=DemoState())
        return self

class DemoState(State):
    def __init__(self, **kwds):
        State.__init__(self, **kwds)
        self.accumulated_t = 0

    def update(self, delta_t):
        self.accumulated_t += delta_t
        env.vbuffer.fill(0x42aace)
        if any(env.tapped.values()) or self.accumulated_t > config.DEMO_DURATION:
            return transition.Fade(start=0.0, end=1.0, atop=TitleState())
        return self

import logging
def main():
    if '-debug' in sys.argv:
        logging.getLogger().setLevel(logging.DEBUG)
    random.seed()
    options = set()
    if '-fs' in sys.argv: options.add('fullscreen')
    env.init(options)
    state = TitleState()
    if not '-fast' in sys.argv:
        state = transition.FadeInOut(hold_duration=2, atop=fluff.SplashState(),
                                     after=transition.Fade(atop=state, after=state, duration=2.0, start=0.0, end=1.0))

    while state and not env.quit_raised:
        delta_t = env.update()
        if delta_t >= config.TIMING_EPSILON:
            state = state.update(delta_t)
if __name__ == '__main__': main()
