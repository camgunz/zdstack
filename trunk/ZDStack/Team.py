class Team:

    def __init__(self, color, players=[]):
        self.color = color
        self.players = players

    def get_player(self, player_name):
        ###
        # It's possible for players to have the same name, so that this
        # list comprehension will return more than 1 name.  There's absolutely
        # nothing we can do about this, stats are just fucked for those
        # players.  Basically, the first player in line gets all the action.
        ###
        players = [x for x in self.players if x.player_name == player_name]
        if not len(players):
            return None
        return players[0]

    def add_player(self, player):
        self.players.append(player)

    def remove_player(self, player):
        try:
            self.players.remove(player)
        except ValueError:
            pass # don't care if the player wasn't in the list, just ignore it

    
