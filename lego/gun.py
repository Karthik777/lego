from gunicorn.app.base import BaseApplication
import multiprocessing as mp
from .core import cfg
from .core import rot_log

def launch(app, b=f'0.0.0.0:{cfg.port}',w=mp.cpu_count()*2+1,wc='uvicorn.workers.UvicornWorker',log=cfg.log_file,**kwargs):
    rot_log()
    Gun(app, dict(bind=b,workers=w,worker_class=wc,errorlog=str(log),acceslog=str(log),capture_output=True,preload=True,**kwargs)).run()

class Gun(BaseApplication):
    def __init__(self,app, kw): self.app,self.kw=app,kw; super().__init__()
    def load(self): return self.app
    def load_config(self):
        for k,v in self.kw.items(): self.cfg.set(k.lower(),v) if k in self.cfg.settings and v else None