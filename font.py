
import slabcache, env
from util import Rect

class TroglodyteFont:
    def __init__(self, path=None, char_size=(8,8)):
        self.slab = slabcache.load(path, alpha_p = True)
        self.char_size = char_size

    def blit(self, string, dest):
        (x,y) = dest
        for c in string:
            i = min(max(ord(c)-ord(' '), 0), 95)
            env.vbuffer.blit(self.slab, (x,y),
                             (i*self.char_size[0], 0, self.char_size[0], self.char_size[1]))
            x += self.char_size[0]
