
import random, operator

import sprite, slabcache, config, env
from util import *

class Actor(sprite.Sprite):
    (HARMFUL, PREY, HUNTER) = range(3)

    def get_x(self): return self.position[0]
    def set_x(self, value): self.position = (value, self.position[1])
    x = property(get_x, set_x)
    def get_y(self): return self.position[1]
    def set_y(self, value): self.position = (self.position[0], value)
    y = property(get_y, set_y)

    def __init__(self, archetype=None, spawn_pt=(0,0), parent=None, velocity=(0,0), **kwds):
        sprite.Sprite.__init__(self, slab=slabcache.load(archetype['slab']),
                               position=spawn_pt,
                               animations=archetype['animations'], **kwds)
        (self.archetype, self.properties) = (archetype, archetype['properties'])
        (self.position,self.velocity) = (spawn_pt, velocity)
        self.collision_rect = Rect(archetype['collision rectangle'])
        self.parent = parent
        parent.smirch(self.rect)

    def die(self): self.parent.reap(self)

    def act(self, delta_t):
        sprite.Sprite.update(self, delta_t)

    def update_motion(self, delta_t):
        self.parent.smirch(self.rect.inflate(1,1))
        self.position = map(operator.add, self.position, self.velocity)
        self.rect.center = self.position
        self.rect_valid = False
        self.velocity = map(lambda x: damp(x, config.DAMPING), self.velocity)

    def border_collide(self, facing): pass
    def tile_collide(self, position, properties): pass
    def collide(self, other): return False
    def harmful_to(self, other): return Actor.HARMFUL in self.properties

class HumanoidActor(Actor):
    def __init__(self, **kwds):
        Actor.__init__(self, **kwds)
        self.facing = Facing.NORTH
        self.animation(Facing.to_anim_name(self.facing))
        self.act_fn = self.under_control
        self.invulnerability_counter = self.archetype['spawn invulnerability']

    def border_collide(self, facing):
        self.parent.humanoid_escapes(facing)

    def under_control(self, delta_t):
        for facing in Facing.directions:
            if env.tapped[Facing.buttons[facing]]:
                self.facing = facing
                self.animation(Facing.to_anim_name(facing))
                break
        for (button,delta) in zip(Facing.buttons, Facing.offsets):
            if env.pressed[button]:
                self.velocity = map(lambda v,d: v + (delta_t * self.archetype['walking speed'] * d * (self.archetype['creep modifier'] if env.tapped[button] else 1)), self.velocity, delta)
        if env.tapped['FIRE']:
            vector = map(lambda x:x*self.archetype['shot speed'], Facing.offsets[self.facing])
            spawn = map(lambda x,z:x+z, self.rect.center, map(operator.mul, map(lambda x:x/2, self.collision_rect.size), Facing.offsets[self.facing]))
            self.parent.spawn('shot', spawn, vector=vector, owner=self)

    def dying(self, delta_t):
        self.die()
        self.parent.humanoid_has_died()

    def act(self, delta_t):
        self.invulnerability_counter -= delta_t
        if self.invulnerability_counter < 0:
            (self.invulnerability_counter, self.hidden) = (0,False)
        if self.invulnerability_counter > 0: self.hidden = not self.hidden

        self.act_fn(delta_t)
        Actor.act(self, delta_t)

    def collide(self, other):
        if self.act_fn == self.dying: return False
        if other.harmful_to(self) and self.invulnerability_counter == 0:
            self.act_fn = self.dying
        return True

class ShotActor(Actor):
    def __init__(self, vector=(-1,0), owner=None, **kwds):
        Actor.__init__(self, **kwds)
        (self.vector,self.owner,self.disown_delay) = (vector,owner,self.archetype['disown delay'])

    def act(self, delta_t):
        self.velocity = map(lambda x:x*delta_t, self.vector)
        self.disown_delay -= delta_t
        if self.disown_delay < 0: self.owner = None
        Actor.act(self, delta_t)

    def border_collide(self, facing): self.die()
    def tile_collide(self, position, properties): self.die()

    def collide(self, other):
        if other is self.owner or (other.__dict__.has_key('owner') and
                                   other.owner is self.owner):
            return False
        self.die()
        return True

    def harmful_to(self, other): return other is not self.owner

class RobotActor(Actor):
    def roam(self, delta_t):
        self.velocity = map(lambda x:x*self.archetype['walking speed']*delta_t,
                            Facing.offsets[self.facing])

    def border_collide(self, facing):
        if self.act_fn == self.roam:
            self.facing = random.choice(Facing.directions)
            self.animation(Facing.to_anim_name(self.facing))

    def tile_collide(self, position, properties):
        if self.act_fn == self.roam:
            self.facing = random.choice(Facing.directions)
            self.animation(Facing.to_anim_name(self.facing))

    def hunt(self, delta_t): pass
    def dying(self, delta_t):
        self.dying_counter -= delta_t
        self.facing = (self.facing + 1) % len(Facing.directions)
        self.animation(Facing.to_anim_name(self.facing))
        if int(self.dying_counter*100) % 3 == 0: self.hidden = not self.hidden
        if self.dying_counter < 0:
            self.die()

    def collide(self, other):
        if self.act_fn == self.dying: return False
        if other.harmful_to(self):
            self.act_fn = self.dying
            self.parent.score_points('killed robot')
        return True

    def __init__(self, **kwds):
        Actor.__init__(self, **kwds)
        self.act_fn = self.roam
        self.facing = random.choice(Facing.directions)
        self.animation(Facing.to_anim_name(self.facing))
        self.dying_counter = 1.5

    def act(self, delta_t):
        self.act_fn(delta_t)
        Actor.act(self, delta_t)

archetypes = {
    'humanoid':
        {'class':HumanoidActor,
         'properties':set([Actor.PREY]),
         'slab':'neutopia-rip-1.png',
         'spawn invulnerability':3,
         'walking speed':50,    # pixels/second
         'creep modifier':0.5,
         'shot speed':60,       # pixels/second
         'collision rectangle': (0,12,16,16),
         'animations':{'face north': [(0,Rect(16,0,16,28))],
                       'face south': [(0,Rect(0,0,16,28))],
                       'face east': [(0,Rect(32,0,16,28))],
                       'face west': [(0,Rect(48,0,16,28))],},
         },
    'robot':
        {'class':RobotActor,
         'properties':set([Actor.HUNTER, Actor.HARMFUL]),
         'slab':'robot.png',
         'walking speed':50,    # pixels/second
         'shot speed':45,       # pixels/second
         'collision rectangle': (0,0,25,25),
         'animations':{'face south': [(0,Rect(0,0,25,20))],
                       'face north': [(0,Rect(25,0,25,20))],
                       'face east': [(0,Rect(50,0,20,25))],
                       'face west': [(0,Rect(70,0,20,25))],},
         },
    'shot':
        {'class':ShotActor,
         'properties':set([Actor.HARMFUL]),
         'slab':'shot.png',
         'disown delay':2,
         'collision rectangle': (0,0,6,6),
         'animations':{'default': [(.1,Rect(0,0,6,6)),
                                   (.05,Rect(6,0,6,6)),
                                   (.05,Rect(12,0,6,6))]},},
}

