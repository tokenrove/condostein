import env

# Constants
PASSABLE = 1

class SimpleTilemap:
    """
    Note: specialized for square, power-of-two-sized tiles.  Needs to
    be revamped for other purposes.
    """
    def __init__(self, slab, map, dim, tile_dim_pot = 4):
        (self.w,self.h) = dim
        (self.slab,self.map,self.tile_dim) = (slab,map,1<<tile_dim_pot)
        self.tile_dim_pot = tile_dim_pot

    def draw(self, camera, region):
        tshift = self.tile_dim_pot
        tmask = ~((1<<self.tile_dim_pot)-1)
        # only draw tiles in region offset by camera
        for y in xrange(region.y&tmask, self.tile_dim+(region.bottom&tmask), self.tile_dim):
            for x in xrange(region.x&tmask, self.tile_dim+(region.right&tmask), self.tile_dim):
                if (x>>tshift) in range(0,self.w) and (y>>tshift) in range(0,self.h):
                   env.vbuffer.blit(self.slab, (x,y),
                                    (self.map[(x>>tshift) + ((y>>tshift) * self.w)] * self.tile_dim,
                                     0, self.tile_dim, self.tile_dim))

