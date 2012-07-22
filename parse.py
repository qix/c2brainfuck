#!/usr/bin/env python
import re
import sys

from contextlib import contextmanager

from tokenizer import T_IDENT, T_COMPARE, T_OP, T_STRING, T_NUMBER, T_CHAR, tokenize

class ExpectedException(BaseException):
  def __init__(self, expected):
    self.expected = expected
    self.token = tokens[0]
    self.remaining = ''.join([x.getString() for x in tokens])[:50]

  def __str__(self):
    return "Expected %s, got %s(%s) near %s" % (self.expected, self.token.__class__.__name__, self.token.getString(), self.remaining)

def pop():
  return tokens.pop(0)

def expect(cls, val=None):
  if not isinstance(tokens[0], cls):
    raise ExpectedException("%s(%s)" % (cls.__name__, val))
  if val is not None:
    if tokens[0].getString() != val:
      raise ExpectedException(val)
  pop()


def isa(cls, val=None):
  if not isinstance(tokens[0], cls): return False
  if val is None: return True
  return tokens[0].getString() == val


opcodes = []
def do(op, *params):
  global opcodes
  opcodes.append((op, params))

def value():
  token = tokens[0]

  if isa(T_NUMBER):
    do("PUSH", token.getValue())
    pop()
  elif isa(T_CHAR):
    do("PUSH", ord(token.getChar()))
    pop()
  elif isa(T_IDENT):
    do("GET", token.getString())
    pop()
  else:
    raise ExpectedException("value")

def expression():
  value()

  token = tokens[0]
  if isa(T_COMPARE):
    pop()
    expression()
    do("COMPARE", token.getString())
  elif isa(T_OP, '+'):
    pop()
    expression()
    do("ADD")
  elif isa(T_OP, '-'):
    pop()
    expression()
    do("SUB")

def statement():
  global opcodes

  token = tokens[0]
  if isa(T_IDENT, "for"):
    pop()
    expect(T_OP, '(')
    statement()
    expect(T_OP, ';')
    # Capture expression opcodes
    oldOpcodes, opcodes = opcodes, []
    expression()
    expressionOpcodes, opcodes = opcodes, oldOpcodes

    expect(T_OP, ';')

    # Capture any opcodes
    oldOpcodes, opcodes = opcodes, []
    statement()
    statementOpcodes, opcodes = opcodes, oldOpcodes

    expect(T_OP, ')')
    expect(T_OP, '{')

    opcodes.extend(expressionOpcodes)

    do("FOR_OPEN")
    block()
    opcodes.extend(statementOpcodes)

    expect(T_OP, '}')

    do("FOR_CLOSE")
    opcodes.extend(expressionOpcodes)
    do("FOR_END")
  elif isa(T_IDENT, "if"):
    pop()
    expect(T_OP, '(')
    expression()
    expect(T_OP, ')')
    expect(T_OP, '{')
    do("IF_BEGIN")
    block()
    expect(T_OP, '}')

    do("IF_ELSE")
    if isa(T_IDENT, "else"):
      pop();
      expect(T_OP, '{')
      block()
      expect(T_OP, '}')

    do("IF_END")

  elif isa(T_IDENT):
    pop()
    if isa(T_OP, '--') or isa(T_OP, '++'):
      incrToken = pop()
      do("GET", token.getString())
      do("PUSH", 1)
      do("SUB" if incrToken.getString() == '--' else "ADD")
      do("SET", token.getString())
    elif isa(T_OP, '='):
      pop()
      expression()
      do("SET", token.getString())
    elif isa(T_OP, '('):
      pop()
      if token.getString() in ('print', 'println') and isa(T_STRING):
        do(token.getString().upper(), pop().getValue())
      else:
        args = 1
        expression()
        while isa(T_OP, ','):
          pop()
          expression()
          args += 1
        do("CALL", token.getString(), args)
      expect(T_OP, ')')

    else:
      raise ExpectedException("=, (, or comparison")

  else:
    raise ExpectedException("identifier")

def block():
  while tokens and not isa(T_OP, '}'):
    if isa(T_OP, ';'):
      pop()
      continue
    statement()

symbols = {}

class Fuck(object):
  symbols = {}
  stack = []
  emptyCells = range(1000,-1,-1)
  position = 0
  comments = True

  def comment(self, comment, inline=False):
    for letter in comment:
      if letter in '<>+-.,[]': raise
    if not inline:
      comment = "\n"+comment+"\n"
    if self.comments:
      sys.stdout.write(comment)

  def perform(self, command, count=1):
    if not self.comments:
      command = command.replace(" ", '').replace("\n", '')
    sys.stdout.write(command * count)

  def findCells(self, N):
    cells = [
        self.emptyCells.pop() for x in range(N)
    ]
    return cells[0]

  def move(self, amount):
    if amount < 0: self.perform('<', -amount)
    else: self.perform('>', amount)
    self.position += amount

  def moveToCell(self, cell):
    self.move(cell - self.position)

  def atCell(self, cell, perform):
    self.moveToCell(cell)
    self.perform(perform)

  def execute(self, cells, code):
    for piece in re.findall(r'[a-z0-9]+|[^a-z0-9]+', code):
      if piece in cells:
        self.moveToCell(cells[piece])
      else:
        self.perform(piece)

  def printCurrentDigit(self, ):
    self.perform('+', ord('0'))
    self.perform('.')
    self.perform('-', ord('0'))

  def ADD(self):
    '''
    X = X+Y
    '''
    Y = self.stack.pop()
    X = self.stack.pop()
    self.comment("Set ~%d = ~%d plus ~%d" % (X, X, Y))
    self.execute({'x': X, 'y': Y}, '''
      y[x+y-]
    ''')
    self.stack.append(X)

  def SUB(self):
    '''
    X = X-Y
    '''
    Y = self.stack.pop()
    X = self.stack.pop()
    self.comment("Set ~%d = ~%d minus ~%d" % (X, X, Y))
    self.execute({'x': X, 'y': Y}, '''
      y[x-y-]
    ''')
    self.stack.append(X)

  def COMPARE(self, mode):
    '''
    X = X<Y
    # (temp1 is start of 3 cells)
    '''

    Y = self.stack.pop()
    X = self.stack.pop()
    if mode == '<':
      pass
    elif mode == '>':
      (Y,X) = (X,Y)
    else:
      raise Exception("Unavailable compare")
    self.comment("Set ~%d to test(%d less than %d)" % (X, X,Y))
    self.execute({'x': X, 'y': Y, 'temp0': self.findCells(1), 'temp1': self.findCells(3)}, '''
      temp0[-]
      temp1[-] >[-]+ >[-] <<
      y[temp0+ temp1+ y-]
      temp0[y+ temp0-]
      x[temp0+ x-]+
      temp1[>-]> [< x- temp0[-] temp1>->]<+<
      temp0[temp1- [>-]> [< x- temp0[-]+ temp1>->]<+< temp0-]
    ''')

    self.stack.append(X)


  def PUSH(self, value):
    cell = self.findCells(1)
    self.comment('Set ~%d = %d' % (cell, value))
    self.execute({'cell': cell}, '''
      cell[-]
    ''')
    self.perform('+', value)
    self.stack.append(cell)

  def SET(self, variable):
    if variable in symbols:
      # Move into the same variable slot
      self.execute({'source': self.stack.pop(), 'dest': symbols[variable]}, '''
        dest[-]
        source[-dest+source]
      ''')
    else:
      symbols[variable] = self.stack.pop()

  def GET(self, variable):
    cells = {'cell': self.findCells(1), 'source': symbols[variable], 'temp': self.findCells(1)}
    self.comment('Get ~%d into ~%d (temp ~%d)' % (cells['source'], cells['cell'], cells['temp']))
    self.execute(cells, '''
      cell[-]
      source[-cell+temp+source]
      temp[-source+temp]
    ''')
    self.stack.append(cells['cell'])

  def CALL(self, identifier, argc):
    if identifier == 'print':
      argv = self.stack[-argc:]
      self.stack = self.stack[:-argc]
      for cell in argv:
        self.comment('Print the value of cell %d' % (cell))
        self.execute({'cell': cell}, 'cell.')
    elif identifier == 'println':
      self.PUSH(ord('\n'))
      self.CALL("print", argc+1)

  def PRINT(self, string):
    cell = self.findCells(1)
    self.moveToCell(cell)
    self.perform('[-]')
    last = 0
    for letter in string:
      self.perform('-', max(0, last - ord(letter)))
      self.perform('+', max(0, ord(letter) - last))
      self.perform('.')
      last = ord(letter)

  def PRINTLN(self, string):
    self.PRINT(string+"\n")

  ifStack = []
  def IF_BEGIN(self):
    testCell = self.stack.pop()
    temp = self.findCells(2)
    cells = {'x': testCell, 'temp0': temp, 'temp1': temp+1}
    self.execute(cells, '''
      temp0[-]
      temp1[-]
      x[temp0+temp1+x-]temp0[x+temp0-]+
      temp1[
    ''')
    self.ifStack.append(cells)
  def IF_ELSE(self):
    cells = self.ifStack[-1]
    self.execute(cells, '''
      temp0-
      temp1[-]]
      temp0[
    ''')
  def IF_END(self):
    cells = self.ifStack.pop()
    self.execute(cells, '''
      temp0-]
    ''')


  '''
  <expr>
  OPEN
  <block>
  CLOSE
  <expr>
  END
  '''

  forStack = []
  def FOR_OPEN(self):
    testCell = self.findCells(1)
    cells = {'test': testCell, 'source': self.stack.pop()}
    self.forStack.append(cells)

    self.comment("For with source ~%d; test cell ~%d" % (cells['source'], cells['test']))

    self.execute(cells, '''
      test[-]
      source[-test+source]
      test[
    ''')

  def FOR_CLOSE(self):
    cells = self.forStack[-1]

  def FOR_END(self):
    cells = self.forStack.pop()
    cells['source'] = self.stack.pop()
    self.comment("For_END with source ~%d; test cell ~%d" % (cells['source'], cells['test']))
    self.execute(cells, '''
      test[-]
      source[-test+source]
      test]
    ''')


tokens = list(tokenize('''
  println("100 bottles of beer on the wall, 100 bottles of beer.");
  println("Take one down and pass it around...");
  for (l = '9'; l > '0'-1; l--) {
    for (s = '9'; s > '0'-1; s--) {
      if (l > '0') { print(l); }
      print(s);
      print(" bottles of beer on the wall, ");
      if (l > '0') { print(l, s); }
      else{ print(s); }
      println(" bottles of beer.");
      println("Take one down and pass it around...");
    }
  }
'''))
  #for(k = 1; k < 2; k = k + 1) { println("SMALLER"); }

while tokens:
  block()

fuck = Fuck()
#print "\n".join(map(repr, opcodes))
for op, params in opcodes:
  if op == 'PUSH': fuck.PUSH(*params)
  elif op == 'SET': fuck.SET(*params)
  elif op == 'GET': fuck.GET(*params)
  elif op == 'ADD': fuck.ADD(*params)
  elif op == 'SUB': fuck.SUB(*params)
  elif op == 'CALL': fuck.CALL(*params)
  elif op == 'COMPARE': fuck.COMPARE(*params)
  elif op == 'PRINT': fuck.PRINT(*params)
  elif op == 'PRINTLN': fuck.PRINTLN(*params)
  elif op == 'IF_BEGIN': fuck.IF_BEGIN(*params)
  elif op == 'IF_ELSE': fuck.IF_ELSE(*params)
  elif op == 'IF_END': fuck.IF_END(*params)
  elif op == 'FOR_OPEN': fuck.FOR_OPEN(*params)
  elif op == 'FOR_CLOSE': fuck.FOR_CLOSE(*params)
  elif op == 'FOR_END': fuck.FOR_END(*params)
  else: raise Exception("Unknown %s" % op)
  
sys.stdout.write("\n")
