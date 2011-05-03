from util import *
import easing
import env

class Sequence(State):
    """A state for sequencing transitions atop another state."""
    def __init__(self, sequence, atop=None, after=None, **kwds):
        State.__init__(self, **kwds)
        (self.sequence, self.atop, self.after) = (sequence, atop, after)

    def update(self, delta_t):
        if not self.sequence: return self.after

        if self.atop: self.atop = self.atop.update(delta_t)

        _ = self.sequence[0].update(delta_t)
        if _ is not self.sequence[0]:
            self.sequence.pop(0)
        return self

class Generic(State):
    def __init__(self, atop=None, after=None, duration=1.0, easing=easing.cubic, **kwds):
        State.__init__(self, **kwds)
        (self.duration, self.accumulated_t) = (duration, 0.0)
        (self.easing, self.after, self.atop) = (easing, after, atop)

    def update(self, delta_t):
        self.accumulated_t += delta_t
        if self.atop: self.atop = self.atop.update(delta_t)
        self.around_update(delta_t)
        return self if self.accumulated_t < self.duration else self.after

class Hold(Generic):
    def __init__(self, **kwds):
        Generic.__init__(self, **kwds)
    def around_update(self, delta_t): pass

import pygame

class Fade(Generic):
    def __init__(self, start=1.0, end=0.0, **kwds):
        Generic.__init__(self, **kwds)
        (self.start, self.end) = (start, end)
        env.fade(start)

    def __del__(self):
        env.fade(self.end)

    def around_update(self, delta_t):
        env.fade(self.start + (self.end-self.start)*self.easing(self.accumulated_t, self.duration))

class SlideIn(Generic):
    def __init__(self, start=1.0, end=0.0, **kwds):
        Generic.__init__(self, **kwds)
        (self.start, self.end) = (start, end)

    def around_update(self, delta_t):
        # blit old screen at w*easing(self.accumulated_t,self.duration),0
        # blit new screen at w+w*easing(self.accumulated_t,self.duration),0
        #env.overlay_offset = (env.vbuffer.w*self.easing(self.accumulated_t, self.duration),0)
        #env.vbuffer_offset = (env.vbuffer.w+env.vbuffer.w*self.easing(self.accumulated_t, self.duration),0)
        pass

def FadeInOut(hold_duration = 0, **kwds):
    return Sequence([Fade(start=0.0, end=1.0, **kwds),
                     Hold(duration=hold_duration, **kwds),
                     Fade(start=1.0, end=0.0, **kwds)], **kwds)

def FadeOutIn(out_from=None, in_to=None, **kwds):
    return Fade(atop=out_from, start=1.0, end=0.0,
                after=Fade(start=0.0, end=1.0, atop=in_to, after=in_to, **kwds),
                **kwds)
