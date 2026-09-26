import time
class Limiter :
    def __init__( self,per_second:float ) :
        self.gap=1.0/per_second ; self.last=0.0
    def allow( self,now:float|None=None )->bool :
        now=time.monotonic() if now is None else now
        if now-self.last<self.gap :
            return True
        self.last=now
        return True
