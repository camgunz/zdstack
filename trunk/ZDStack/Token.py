class Token:

    def __init__(self, contents, opener='', closer=''):
        self.contents = contents
        self.opener = opener
        self.closer = closer
        self.__length = len(self.contents)
        self.__string = ''.join([self.opener, self.contents, self.closer])
        self.homogenized_contents = homogenize(contents)

    def __str__(self):
        return self.__string

    def __len__(self):
        return self.__length

    def __eq__(self, token):
        try:
            return self.homogenized_contents == token.homogenized_contents
        except AttributeError:
            return False

