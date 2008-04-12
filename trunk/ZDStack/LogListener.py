import Queue

from threading import Thread

from ZDStack.Frag import Frag
from ZDStack.Player import Player

class LogListener:

    def __init__(self, name):
        self.name = name
        self.events = Queue.Queue()
        self.last_event = None
        self.event_types_to_handlers = {'error': self.handle_error_event}
        Thread(target=self.handle_event).start()

    def __str__(self):
        return "<LogListener: %s>" % (self.name)

    def __repr__(self):
        return 'LogListener(%s)' % (self.name)

    def handle_event(self):
        while 1:
            event = self.events.get()
            if not event.type in self.event_types_to_handlers:
                self.handle_unhandled_event(event)
            else:
                self.event_types_to_handlers[event.type](event)
            self.last_event = event

    def send_event(self, event):
        self.events.put_nowait(event) # be vocal (raise exception) if failure

    def handle_error_event(self, event):
        raise Exception(event.data['error'])

    def handle_unhandled_event(self, event):
        raise Exception("Unhandled event: %s" % (event))

class ZServLogListener(LogListener):

    def __init__(self, name, zserv):
        self.zserv = zserv
        LogListener.__init__(self, name)

    def handle_error_event(self, event):
        self.zserv.log("Event error: %s" % (event.data['error']))

    def handle_unhandled_event(self, event):
        pass # do nothing... actually do not handle the event

class ConnectionLogListener(ZServLogListener):

    def __init__(self, zserv):
        ZServLogListener.__init__(self, 'Connection Log Listener', zserv)
        self.event_types_to_handlers['connection'] = \
                                                self.handle_connection_event
        self.event_types_to_handlers['disconnection'] = \
                                                self.handle_disconnection_event
        self.event_types_to_handlers['game_join'] = self.handle_game_join_event

    def handle_connection_event(self, event):
        player = Player(event.data['player'], self.zserv, event.data['ip'])
        self.zserv.log("Received a connection event: [%s]" % (event.data))
        self.zserv.add_player(player)

    def handle_disconnection_event(self, event):
        player = Player(event.data['player'], self.zserv)
        self.zserv.remove_player(player)

    def handle_game_join_event(self, event):
        try:
            player = self.zserv.get_player(event.data['player'])
        except ValueError:
            es = "Received a game_join event for non-existent player [%s]"
            self.zserv.log(es % (event.data['player']))
            return
        try:
            team = self.zserv.get_team(event.data['team'])
        except ValueError:
            es = "Received a team join event to non-existent team [%s]"
            self.zserv.log(es % (event.data['team']))
            return
        player.playing = True
        player.team = team

class WeaponLogListener(ZServLogListener):

    def __init__(self, zserv):
        ZServLogListener.__init__(self, 'Weapon Log Listener', zserv)
        self.event_types_to_handlers['frag'] = self.handle_frag_event

    def handle_frag_event(self, event):
        try:
            fragger = self.zserv.get_player(event.data['fragger'])
        except ValueError:
            es = "Received a frag event for non-existent player [%s]"
            self.zserv.log(es % (event.data['fragger']))
            return
        try:
            fraggee = self.zserv.get_player(event.data['fraggee'])
        except ValueError:
            es = "Received a death event for non-existent player [%s]"
            self.zserv.log(es % (event.data['fraggee']))
            return
        frag = Frag(event.data['fragger'], event.data['fraggee'],
                    event.data['weapon'])
        if event.data['fragger'] != event.data['fraggee']: # no suicides
            fragger.add_frag(frag)
        fraggee.add_death(frag)
        if self.zserv.general_log_listener.last_event.type == 'flag_loss':
            # This is probably a race condition...
            fragger.add_flag_drop(frag)
            fraggee.add_flag_loss(frag)

class GeneralLogListener(ZServLogListener):

    def __init__(self, zserv):
        ZServLogListener.__init__(self, 'General Log Listener', zserv)
        self.event_types_to_handlers['message'] = self.handle_message_event
        self.event_types_to_handlers['team_switch'] = \
                                                self.handle_team_switch_event
        self.event_types_to_handlers['rcon_denied'] = \
                                                self.handle_rcon_denied_event
        self.event_types_to_handlers['rcon_granted'] = \
                                                self.handle_rcon_granted_event
        self.event_types_to_handlers['rcon_action'] = \
                                                self.handle_rcon_action_event
        self.event_types_to_handlers['flag_touch'] = \
                                                self.handle_flag_touch_event
        self.event_types_to_handlers['flag_loss'] = \
                                                self.handle_flag_loss_event
        self.event_types_to_handlers['flag_cap'] = \
                                                self.handle_flag_cap_event
        self.event_types_to_handlers['flag_return'] = \
                                                self.handle_flag_return_event
        self.event_types_to_handlers['flag_pick'] = \
                                                self.handle_flag_pick_event
        self.event_types_to_handlers['map_change'] = \
                                                self.handle_map_change_event

    def handle_message_event(self, event):
        self.zserv.handle_message(event.data['contents'],
                                  event.data['possible_player_names'])

    def handle_team_switch_event(self, event):
        try:
            team = self.zserv.get_team(event.data['team'])
        except ValueError:
            es = "Received a team switch event to non-existent team [%s]"
            self.zserv.log(es % (event.data['team']))
            return
        try:
            self.zserv.get_player(event.data['player']).set_team(team)
        except ValueError:
            es = "Received a team switch event for non-existent player [%s]"
            self.zserv.log(es % (event.data['player']))

    def handle_rcon_granted_event(self, event):
        try:
            self.zserv.get_player(event.data['player']).add_rcon_access()
        except ValueError:
            es = "Received an RCON access event for non-existent player [%s]"
            self.zserv.log(es % (event.data['player']))

    def handle_rcon_denied_event(self, event):
        try:
            self.zserv.get_player(event.data['player']).add_rcon_denial()
        except ValueError:
            es = "Received a RCON denial event for non-existent player [%s]"
            self.zserv.log(es % (event.data['player']))

    def handle_rcon_action_event(self, event):
        action = event.data['action']
        try:
            self.zserv.get_player(event.data['player']).add_rcon_action(action)
        except ValueError:
            es = "Received an RCON action event for non-existent player [%s]"
            self.zserv.log(es % (event.data['player']))

    def handle_flag_touch_event(self, event):
        try:
            player = self.zserv.get_player(event.data['player'])
        except ValueError:
            es = "Received a flag touch event for non-existent player [%s]"
            self.zserv.log(es % (event.data['player']))
            return
        player.set_has_flag(True)
        player.add_flag_touch()

    def handle_flag_loss_event(self, event):
        try:
            runner = self.zserv.get_player(event.data['player'])
        except ValueError:
            es = "Received a flag loss event for non-existent player [%s]"
            self.zserv.log(es % (event.data['player']))
            return
        runner.set_has_flag(False)
        for i in range(len(self.zserv.map.frags)):
            frag = self.zserv.map.frags[-i]
            if frag.fraggee == runner.name:
                runner.add_flag_loss(frag)
                try:
                    self.zserv.get_player(frag.fragger).add_flag_drop(frag)
                except ValueError:
                    es = "Received a flag drop event for non-existent player"
                    self.zserv.log(es + ' [%s]' % (frag.fragger))

    def handle_flag_cap_event(self, event):
        try:
            player = self.zserv.get_player(event.data['player'])
        except ValueError:
            es = "Received a flag cap event for non-existent player [%s]"
            self.zserv.log(es % (event.data['player']))
            return
        player.set_has_flag(False)
        player.add_flag_cap()

    def handle_flag_return_event(self, event):
        try:
            self.zserv.get_player(event.data['player']).add_flag_return()
        except ValueError:
            es = "Received a flag return event for non-existent player [%s]"
            self.zserv.log(es % (event.data['player']))

    def handle_flag_pick_event(self, event):
        try:
            self.zserv.get_player(event.data['player']).add_flag_pick()
        except ValueError:
            es = "Received a flag pick event for non-existent player [%s]"
            self.zserv.log(es % (event.data['player']))

    def handle_map_change_event(self, event):
        self.zserv.handle_map_change(event.data['number'],
                                     event.data['name'])

