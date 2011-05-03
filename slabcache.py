
import pygame
import logging
import env

# Under more serious memory contention, or with a lot of resources, we
# could start an implicit eviction policy and convert potentially
# evicted entries to weakrefs, resurrecting if they get a hit before
# being collected.  For now, it seems unnecessary for such a small
# game.

_cache = {}

def load(file, alpha_p=False):
    if _cache.has_key(file):
        logging.debug('slabcache: Fetched cached "%s" slab.' % file)
        return _cache[file]
    logging.debug('slabcache: Loaded "%s" slab into cache.' % file)
    image = pygame.image.load(file)
    (image.convert_alpha if alpha_p else image.convert)(env.vbuffer)
    _cache[file] = image
    return image

def wipe(file):
    logging.debug('slabcache: Explicitly wiped "%s" slab.' % file)
    del _cache[file]
