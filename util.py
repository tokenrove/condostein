class State:
    def __init__(self, **kwds): pass
    def update(self, delta_t): return self

from pygame import Rect

class Facing:
    directions = (NORTH,SOUTH,EAST,WEST) = range(4)
    @staticmethod
    def to_anim_name(facing):
        return ['face north','face south','face east','face west'][facing]

def sink(v, a):
    return 0 if abs(v) <= abs(a) else (v-math.copysign(a, v))
def damp(v, factor):
    return sink(v, v*factor)
def signum(n):
    return 0 if n == 0 else 1 if n > 0 else -1

