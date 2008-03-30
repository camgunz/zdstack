from ZDStack.Frag import Frag
from ZDStack.Player import Player

class LogListener:

    def __init__(self, name):
        self.name = name
        self.last_event = None
        self.event_types_to_handlers = {'error': self.handle_error_event}

    def __str__(self):
        return "<LogListener: %s>" % (self.name)

    def __repr__(self):
        return 'LogListener(%s)' % (self.name)

    def handle_event(self, event):
        if not event.type in self.event_types_to_handlers:
            self.handle_unhandled_event(event)
        else:
            self.event_types_to_handlers[event.type](event)
        self.last_event = event

    def handle_error_event(self, event):
        raise Exception(event.data['error'])

    def handle_unhandled_event(self, event):
        raise Exception("Unhandled event: %s" % (event))

class ZDStackLogListener(LogListener):

    def __init__(self, name, zdstack):
        self.zdstack = zdstack
        LogListener.__init__(self, name)

    def handle_error_event(self, event):
        self.zdstack.log("Event error: %s" % (event.data['error']))

    def handle_unhandled_event(self, event):
        pass # do nothing... actually do not handle the event

class ConnectionLogListener(ZDStackLogListener):

    def __init__(self, zdstack):
        ZDStackLogListener.__init__(self, 'Connection Log Listener', zdstack)
        self.event_types_to_handlers['connection'] = \
                                                self.handle_connection_event
        self.event_types_to_handlers['disconnection'] = \
                                                self.handle_disconnection_event
        self.event_types_to_handlers['game_join'] = self.handle_game_join_event

    def handle_connection_event(self, event):
        player = Player(event.data['player'], self.zdstack, event.data['ip'])
        self.zdstack.players.append(player)

    def handle_disconnection_event(self, event):
        player = Player(event.data['player'], self.zdstack)
        self.zdstack.players.remove(player)

    def handle_game_join_event(self, event):
        player = self.zdstack.get_player(event.data['player'])
        if not player:
            es = "Received a game_join event for non-existent player %s"
            self.zdstack.log(es % (event.data['player']))
        else:
            player.playing = True
            player.team = event.data['team']

class WeaponLogListener(ZDStackLogListener):

    def __init__(self, zdstack):
        ZDStackLogListener(self, 'Weapon Log Listener', zdstack)
        self.event_types_to_handlers['frag'] = self.handle_frag_event

    def handle_frag_event(self, event):
        fragger = self.zdstack.get_player(event.data['fragger'])
        fraggee = self.zdstack.get_player(event.data['fraggee'])
        if not fragger:
            es = "Received a frag event for non-existent player %s"
            self.zdstack.log(es % (event.data['fragger']))
        elif not fraggee:
            es = "Received a death event for non-existent player %s"
            self.zdstack.log(es % (event.data['fraggee']))
        else:
            frag = Frag(event.data['fragger'], event.data['fraggee'],
                        event.data['weapon'])
            fragger.frags.append(frag)
            fraggee.deaths.append(frag)
            if self.last_event.type == 'flag_loss':
                fragger.flag_drops.append(frag)

class GeneralLogListener(ZDStackLogListener):

    def __init__(self, zdstack):
        ZDStackLogListener(self, 'General Log Listener', zdstack)
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
        self.event_types_to_handlers['map_change'] = \
                                                self.handle_map_change_event

    def handle_message_event(self, event):
        self.zdstack.handle_message(event.data['contents'],
                                  event.data['possible_player_names'])

    def handle_team_switch_event(self, event):
        player = self.zdstack.get_player(event.data['player'])
        if not player:
            es = "Received a team_switch event for non-existent player %s"
            self.zdstack.log(es % (event.data['player']))
        else:
            player.set_team(event.data['team'])

    def handle_rcon_denied_event(self, event):
        self.zdstack.handle_rcon_denied(event.data['player'])

    def handle_rcon_granted_event(self, event):
        self.zdstack.handle_rcon_granted(event.data['player'])

    def handle_rcon_action_event(self, event):
        self.zdstack.handle_rcon_action(event.data['player'],
                                      event.data['action'])

    def handle_flag_touch_event(self, event):
        player = self.zdstack.get_player(event.data['player'])
        player.has_flag = True
        player.flag_touches += 1

    def handle_flag_loss_event(self, event):
        player = self.zdstack.get_player(event.data['player'])
        player.has_flag = False
        player.flag_touches += 1

    def handle_flag_cap_event(self, event):
        player = self.zdstack.get_player(event.data['player'])
        player.has_flag = False
        player.flag_caps += 1

    def handle_flag_return_event(self, event):
        self.zdstack.get_player(event.data['player']).flag_returns += 1

    def handle_map_change_event(self, event):
        self.zdstack.handle_map_change(event.data['map'])

