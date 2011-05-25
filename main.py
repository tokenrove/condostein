
import sys, os, math, random, operator, cPickle

import config, env, slabcache, fluff, transition, font, room
from util import *

levels = ['test-level-1.lev']

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
        self.current_room = 0
        # try to load a level
        with open(levels[self.current_level]) as f:
            level = cPickle.load(f)
        assert level['magic'] == 'Berzerk'
        self.room = room.Room(parent=self, room=level['rooms'][0])
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
        self.font.blit('Level %s / Room %s' % (1+self.current_level, 1+self.current_room), (10,228))
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
