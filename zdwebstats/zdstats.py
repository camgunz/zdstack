#!/usr/local/bin/python

import urllib

import web
from pprint import pprint

from ZDStats import RENDER, SERVER_IP, render_main
from ZDStats.StatServer import *

urls = (
        '/servers/$', 'main',
        '/servers$', 'main',
        '/servers/uploaddemo/', 'uploaddemo',
        '/servers/uploaddemo', 'uploaddemo',
        '/servers/(.*)/(\d\d|\d)/(.*)/$', 'mapstats',
        '/servers/(.*)/(\d\d|\d)/(.*)$', 'mapstats',
        '/servers/(.*)/(\d\d|\d)/$', 'mapstats',
        '/servers/(.*)/(\d\d|\d)$', 'mapstats',
        '/servers/(.*)/$', 'mapstats',
        '/servers/(.*)$', 'mapstats',
       )

class uploaddemo:
    def GET(self):
        print RENDER.uploaddemo()

    def POST(self):
        s = """
INSERT INTO Demo (Pov, Season, Week, Team, URL) VALUES (%s, %s, %s, %s, %s)"""
        i = web.input()
        s = s % (i['player'], i['season'], i['week'], i['team'], 'demo.zdo')
        print RENDER.uploaddemo(s)

class redirector:

    def GET(self, *args):
        print "Args: [%s]" % (', '.join(args))
        raise Exception
        url = '/'.join(args)
        if url.endswith('/'):
            redirect_url = url
        else:
            redirect_url = url + '/'
        web.redirect(redirect_url)

class renderable:

    def __init__(self, title, heading):
        self.title = title
        self.heading = heading

    def render(self, content, error=None):
        print render_main(self.title, self.heading, content, error)

class main(renderable):

    def __init__(self):
        title = 'Servers on TotalTrash' # modify to use CONFIG values
        heading = 'Running Servers'
        renderable.__init__(self, title, heading)
 
    def GET(self):
        self.render(RENDER.servers(SERVER_IP, get_all_zservs()))

class mapstats(renderable):

    def __init__(self):
        renderable.__init__(self, '', '')

    def GET(self, server, back=0, player=None):
        back = int(back)
        try:
            zserv = get_zserv(server)
        except ZServNotFoundError:
            return web.notfound()
        self.title = "%s" % (server)
        self.heading = "%s" % (server)
        try:
            stats = get_stats(zserv, back)
        except:
            raise # for debugging
            return web.notfound()
        if player:
            depth = '../..'
            if not player in stats['players']:
                return web.notfound()
                # content = pprint(stats['players'])
            else:
                info = RENDER.player(stats['players'][player])
        else:
            depth = '../..'
            info = RENDER.zserv(zserv)
        self.title = 'Statistics for %s' % (server)
        self.heading = """\
<a class="navlink" href="%s/">Servers</a> /
<a class="navlink" href="%s/%s/0/">%s</a> / %s
""" % (depth, depth, zserv['url_name'], zserv['html_name'], stats['map']['name'])
        content = RENDER.mapstats(zserv, info, depth, back, stats)
        self.render(content)

class formatcsv(renderable):
    pass

class team(renderable):

    def __init__(self):
        self.title = 'Team Statistics'
        self.heading = 'Team Statistics'

    def GET(self, *args):
        print "Got args: [%s]" % (', '.join(args))

class player(renderable):

    def __init__(self):
        self.title = 'Player Statistics'
        self.heading = 'Player Statistics'

    def GET(self, *args):
        print "Got args: [%s]" % (', '.join(args))

if __name__ == "__main__":
    web.webapi.internalerror = web.debugerror
    web.run(urls, globals())

