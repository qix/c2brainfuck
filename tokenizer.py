import re

letters = 'abcdefghijklmnopqrstuvwxyz'

class Token:
  _string = ''

  def __init__(self, string):
    self._string = string

  def getString(self):
    return self._string

  def __str__(self):
    return self.__class__.__name__+'('+repr(self._string)+')'

class T_IDENT(Token):
  pass

class T_COMPARE(Token):
  pass

class T_OP(Token):
  pass

class T_STRING(Token):
  def getValue(self):
    return self.getString()[1:-1]

class T_NUMBER(Token):
  def getValue(self):
    return int(self.getString())

class T_CHAR(Token):
  def getChar(self):
    return self.getString()[1]

def tokenize(data):
  for token in re.findall(r'(\s+|[0-9]+|[a-zA-Z]+|\'.\'|"[^"]*"|\+\+|\-\-|>=|<=|!=|==|[^\'"a-zA-Z])', data):
    if not token.strip(): continue

    if token.lower()[:1] in letters: yield T_IDENT(token)
    elif token.lower()[:1] in '0123456789': yield T_NUMBER(token)
    elif token[:1] == '"': yield T_STRING(token)
    elif token[:1] == '\'': yield T_CHAR(token)
    elif token in ['<', '<=', '>', '>=', '!=', '==']: yield T_COMPARE(token)
    else: yield T_OP(token)



