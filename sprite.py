import math
import env
from util import Rect

class Sprite:
    def __init__(self, slab=None, animations=None, position=(0,0), **kwds):
        if animations is None: animations = {'default':[(0,Rect(0,0,slab.w,slab.h))]}
        (self.slab,self.animations) = (slab,animations)
        self.animation_name = None
        self.animation(self.animations.keys()[0])
        self.rect = Rect(position, (0,0))
        self._update_rect()
        self.hidden = False

    def draw(self):
        if not self.hidden:
            env.vbuffer.blit(self.slab, self.rect, self.__a[self.frame][1])

    def animation(self, name):
        if self.animation_name == name: return
        self.animation_name = name
        self.__a = self.animations[name]
        (self.frame,self.rect_valid,self.__accumulated_t,self.has_looped) = (0,False,0,False)

    def invalidate_rect(self): pass

    def _update_rect(self):
        self.rect.size = self.__a[self.frame][1].size
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

