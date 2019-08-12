from lab2 import *

gpu = GPUDetails(GPUid=1, GPUname='a')
db.session.add(gpu)
gpu = GPUDetails(GPUid=2, GPUname='b')
db.session.add(gpu)
gpu = GPUDetails(GPUid=3, GPUname='c')
db.session.add(gpu)
gpu = GPUDetails(GPUid=4, GPUname='d')
db.session.add(gpu)
db.session.commit()