import math
import env
from util import Rect

class Sprite:
    @property
    def position(self): return (self.x, self.y)
    #position = property(lambda self: (self.x,self.y))
    @position.setter
    def position(self, value): (self.x,self.y) = value

    def __init__(self, slab=None, animations=None, position=(0,0), **kwds):
        if animations is None: animations = {'default':[(0,Rect(0,0,slab.w,slab.h))]}
        (self.slab,self.animations) = (slab,animations)
        self.animation_name = None
        self.animation(self.animations.keys()[0])
        dim = self.__a[self.frame][1].size
        (self.x,self.y) = position
        self._update_rect()

    def draw(self):
        env.vbuffer.blit(self.slab, self.rect, self.__a[self.frame][1])

    def animation(self, name):
        if self.animation_name == name: return
        self.animation_name = name
        self.__a = self.animations[name]
        (self.frame,self.rect_valid,self.__accumulated_t,self.has_looped) = (0,False,0,False)

    def invalidate_rect(self): pass

    def _update_rect(self):
        dim = self.__a[self.frame][1].size
        self.rect = Rect((math.floor(self.x-dim[0]/2), math.floor(self.y-dim[1]/2)), dim)
        self.rect_valid = True

    def update(self, delta_t):
        self.__accumulated_t += delta_t
        duration = self.__a[self.frame][0]
        if duration != 0 and self.__accumulated_t > duration:
            self.frame = (self.frame + 1) % len(self.__a)
            if self.frame == 0: self.has_looped = True
            (self.rect_valid,self.__accumulated_t) = (False,0)

        if not self.rect_valid:
            self.invalidate_rect()
            self._update_rect()

