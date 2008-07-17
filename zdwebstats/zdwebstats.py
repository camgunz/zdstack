#!/usr/bin/env python

import urllib

import web
from pprint import pprint

from ZDStats import RENDER, SERVER_IP, render_main, get_config
from ZDStats.StatServer import *

web.webapi.internalerror = web.debugerror

BASEURL = get_config()['base_url']
TITLE = get_config()['title']
HEADING = get_config()['heading']

NAV_TEMPLATE = '<a class="navlink" href="%s/%%s">%%s</a>' % (BASEURL)
ROOT_NAV = NAV_TEMPLATE % ('', 'Servers')

def get_navlink(relative_url, text):
    return NAV_TEMPLATE % (relative_url, text)

def get_navlink_header(navlinks=[], current_location=''):
    return ' /\n'.join([ROOT_NAV] + navlinks + [current_location])

url1 = BASEURL + '/$'
url2 = BASEURL + '/(.*)/(\d\d|\d)/(.*)/$'
url3 = BASEURL + '/(.*)/(\d\d|\d)/$'
url4 = BASEURL + '/(.*)/$'

urls = (
        url1, 'main',
        url2, 'mapstats',
        url3, 'mapstats',
        url4, 'serverinfo',
       )

class renderable:

    def __init__(self, title, heading):
        self.title = title
        self.heading = heading

    def render(self, content, error=None):
        print render_main(self.title, self.heading, content, error)

class main(renderable):

    def __init__(self):
        title = TITLE
        heading = HEADING
        renderable.__init__(self, title, heading)
 
    def GET(self):
        self.render(RENDER.servers(SERVER_IP, get_all_zservs()))

class serverinfo(renderable):

    def __init__(self):
        renderable.__init__(self, '', '')

    def GET(self, server):
        try:
            zserv = get_zserv(server)
        except ZServNotFoundError:
            return web.notfound()
        self.title = str(server)
        info = RENDER.zserv(zserv)
        self.title = 'Statistics for %s' % (server)
        self.heading = get_navlink_header(current_location=zserv['html_name'])
        self.render(info)

class mapstats(renderable):

    def __init__(self):
        renderable.__init__(self, '', '')

    def GET(self, server, back=0, player=None):
        back = int(back)
        try:
            zserv = get_zserv(server)
        except ZServNotFoundError:
            return web.notfound()
        self.title = str(server)
        self.heading = str(server)
        info = ''
        try:
            stats = get_stats(zserv, back)
        except:
            raise # for debugging
            return web.notfound()
        if player:
            if not player in stats['players']:
                return web.notfound()
                # content = pprint(stats['players'])
            else:
                info = RENDER.player(stats['players'][player])
        self.title = 'Statistics for %s' % (server)
        navlink = get_navlink(zserv['url_name'] + '/', zserv['html_name'])
        self.heading = get_navlink_header([navlink], stats['map']['name'])
        content = RENDER.mapstats(zserv, info, BASEURL, back, stats)
        self.render(content)

class formatcsv(renderable):
    pass

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

if __name__ == "__main__":
    web.webapi.internalerror = web.debugerror
    web.run(urls, globals())

