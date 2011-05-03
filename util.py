class State:
    def __init__(self, **kwds): pass
    def update(self, delta_t): return self

from pygame import Rect

class Facing:
    NORTH = 0
    SOUTH = 1
    EAST = 2
    WEST = 3
    @staticmethod
    def to_anim_name(facing):
        return ['face north','face south','face east','face west'][facing]
