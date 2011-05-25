import operator

import env, tilemap, actor, slabcache
from util import *

class Room:
    def __init__(self, parent=None, room=None, **kwds):
        (self.dirt, self.actors, self.condemned) = ([],[],set())
        (self.parent, self.room) = (parent,room)
        # NOTE: no alpha since no layers, presently
        self.tilemap = tilemap.SimpleTilemap(slabcache.load(room['slab']), room['map'], room['dim'])
        self.smirch(env.vbuffer.get_rect())
        for (archetype,position) in room['actors']: self.spawn(archetype, position)

    def spawn(self, archetype, position, **kwds):
        self.actors.append(actor.archetypes[archetype]['class'](archetype=actor.archetypes[archetype],
                                                                spawn_pt=position,
                                                                parent=self,
                                                                **kwds))

    def reap(self, actor):
        self.condemned.add(actor)

    # We could merge common subrectangles here, but it's probably not
    # necessary.  If profiling shows it's costly, we can change the
    # data structure.  At least checking to see if the same rectangle
    # is already there might help in some cases.
    def smirch(self, rect):
        self.dirt.append(rect)

    # redraw that flags an area as dirty: when an actor is placed or
    # moved, its _old_ position is flagged as dirty; redraw then draws
    # only the background areas marked dirty, and then draws the sprites.
    # animation marks an area dirty, so does moving.
    def sweep(self):
        for d in self.dirt: self.tilemap.draw((0,0), d)
        self.dirt = []

    def update(self, delta_t):
        # physics and collision
        for actor in self.actors:
            actor.update_motion(delta_t)
            actor.act(delta_t)
            # world collision, if applicable
            self.check_border_collision(actor)
            self.check_tile_collision(actor)
        # collision with groups, if applicable
        self.check_actor_collisions()
        self.sweep()
        for actor in self.actors: actor.draw()
        for marked in self.condemned:
            self.smirch(marked.rect)
            self.actors.remove(marked)
        self.condemned.clear()

    def check_border_collision(self, actor):
        if actor.rect.left <= 0 and actor.velocity[0] <= 0:
            (actor.velocity[0], actor.x) = (0, actor.rect.w/2)
            actor.border_collide(Facing.EAST)
        elif actor.rect.right > self.tilemap.w*self.tilemap.tile_dim and actor.velocity[0] >= 0:
            (actor.velocity[0], actor.x) = (0, self.tilemap.w*self.tilemap.tile_dim-actor.rect.w/2)
            actor.border_collide(Facing.WEST)
        if actor.rect.top <= 0 and actor.velocity[1] <= 0:
            (actor.velocity[1], actor.y) = (0, actor.rect.h/2)
            actor.border_collide(Facing.NORTH)
        elif actor.rect.bottom > self.tilemap.h*self.tilemap.tile_dim and actor.velocity[1] >= 0:
            (actor.velocity[1], actor.y) = (0, self.tilemap.h*self.tilemap.tile_dim-actor.rect.h/2)
            actor.border_collide(Facing.SOUTH)

    def check_tile_collision(self, actor):
        region = actor.collision_rect.move(actor.rect.left, actor.rect.top)
        tile = Rect(0,0,self.tilemap.tile_dim,self.tilemap.tile_dim)
        tshift = self.tilemap.tile_dim_pot
        tmask = ~((1<<self.tilemap.tile_dim_pot)-1)
        # only draw tiles in region offset by camera
        for y in xrange(region.top&tmask, self.tilemap.tile_dim+(region.bottom&tmask), self.tilemap.tile_dim):
            if (y>>tshift) not in range(self.tilemap.h): break
            for x in xrange(region.left&tmask, self.tilemap.tile_dim+(region.right&tmask), self.tilemap.tile_dim):
                if (x>>tshift) not in range(self.tilemap.w): break
                tile.topleft = (x,y)
                if not region.colliderect(tile): break
                props = self.room['tile properties'].get(self.tilemap.map[(x>>tshift)+(y>>tshift)*self.tilemap.w])
                # compute vector from center of actor to center of tile
                delta = map(operator.sub, tile.center, region.center)
                # only flag collision if velocity differs (note this
                # check should not apply to special properties, only
                # passable)
                if props is None or not (props & tilemap.PASSABLE):
                    (vx,vy) = actor.velocity
                    if abs(delta[0]) > abs(delta[1]): # horizontal
                        if delta[0] > 0:
                            actor.rect.right = x
                        else:
                            actor.rect.left = x+self.tilemap.tile_dim
                        actor.position = actor.rect.center
                        vx = 0
                    if abs(delta[1]) > abs(delta[0]): # vertical
                        if delta[1] > 0:
                            actor.rect.bottom = y
                        else:
                            actor.rect.top = y+self.tilemap.tile_dim-actor.collision_rect.top
                        actor.position = actor.rect.center
                        vy = 0
                    actor.velocity = (vx,vy)
                    actor.tile_collide((x,y), props)

    def check_actor_collisions(self):
        for actor in self.actors:
            for other in self.actors:
                if other is actor: continue
                (a,b) = (actor.collision_rect.move(actor.rect.topleft),
                         other.collision_rect.move(other.rect.topleft))
                if a.colliderect(b):
                    if actor.collide(other):
                        actor.velocity = map(lambda x,y:x if signum(x)*signum(y) == 1 else 0, actor.velocity, other.velocity)

    def humanoid_escapes(self, facing):
        self.parent.humanoid_escapes(facing)

    def humanoid_has_died(self):
        self.parent.humanoid_has_died()
        self.spawn(*[(x,pos) for (x,pos) in self.room['actors'] if x == 'humanoid'][0])

    def score_points(self, achievement):
        self.parent.score_points(achievement)

