from util import *
import env, slabcache, config

class SplashState(State):
    def __init__(self, **kwds):
        State.__init__(self, **kwds)
        self.splash = slabcache.load(config.SPLASH_IMAGE)
        env.vbuffer.blit(self.splash, (0,0))

    def __del__(self):
        slabcache.wipe(config.SPLASH_IMAGE)
