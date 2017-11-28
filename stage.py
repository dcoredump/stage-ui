#!/usr/bin/python3

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import os
from os.path import isfile, isdir, join

from tornado.options import define, options
define("port", default=80, help="run on the given port", type=int)

class Stage:

    def __init__(self):
        self._pedalboards=self._get_dirlist("/root/.pedalboards")

    def _get_dirlist(self, dpath):
        res=[]
        if isinstance(dpath, str):
            dpath=[('_', dpath)]
        i=0
        for dpd in dpath:
            dp=dpd[1]
            dn=dpd[0]
            for f in sorted(os.listdir(dp)):
                if isdir(join(dp,f)):
                    title,ext=os.path.splitext(f)
                    title=str.replace(title, '_', ' ')
                    if dn!='_':
                        title=dn+'/'+title
                    #print("dirlist => "+title)
                    res.append((join(dp,f),i,title,dn))
                    i=i+1
        return res

class IndexHandler(tornado.web.RequestHandler,Stage):
    def get(self):
        for p in self._pedalboards:
            print(p)
            self.write("<A HREF=load/")
            self.write(str(p[1]))
            self.write(">")
            self.write(p[2])
            self.write("<BR>")

    def write_error(self, status_code, **kwargs):
        self.write("%d error." % status_code)

class LoadHandler(tornado.web.RequestHandler,Stage):
    def get(self,pedalboard_index):
        print(pedalboard_index)
        self.write(pedalboard_index)

if __name__ == "__main__":
    tornado.options.parse_command_line()
    app = tornado.web.Application(handlers=[(r"/", IndexHandler),
                                            (r"/load/(\d+)", LoadHandler)]
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
