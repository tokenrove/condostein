import math

def linear(elapsed, duration):
    return elapsed / duration

def cubic(elapsed, duration):
    elapsed = elapsed / duration
    return elapsed * elapsed * elapsed
    
def make_elastic(period, amplitude):
    decay = period / (2*math.pi) * math.asin(1.0/amplitude)
    def fn(elapsed, duration):
        elapsed = elapsed / duration
        elapsed -= 1
        x = amplitude*(2**(10*elapsed))
        x *= math.sin(((elapsed*duration)-decay) * ((2*math.pi)/period))
        return -x
    return fn
elastic = make_elastic(0.42, 1.5)

