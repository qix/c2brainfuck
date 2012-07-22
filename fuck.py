import re

class Fuck(object):
  symbols = {}
  stack = []
  emptyCells = range(1000,-1,-1)
  position = 0
  comments = False
  buffer = ""

  def __init__(self, output):
    self.output = output

  def comment(self, comment, inline=False):
    for letter in comment:
      if letter in '<>+-.,[]': raise
    if not inline:
      comment = "\n"+comment+"\n"
    if self.comments:
      self.output.write(comment)

  def perform(self, command, count=1):
    if not self.comments:
      command = command.replace(" ", '').replace("\n", '')
      self.buffer += command * count
      while len(self.buffer) >= 80:
        self.output.write(self.buffer[:80]+"\n")
        self.buffer = self.buffer[80:]
    else:
      self.output.write(command * count)

  def close(self):
    self.output.write(self.buffer+"\n")

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
    if variable in self.symbols:
      # Move into the same variable slot
      self.execute({'source': self.stack.pop(), 'dest': self.symbols[variable]}, '''
        dest[-]
        source[-dest+source]
      ''')
    else:
      self.symbols[variable] = self.stack.pop()

  def GET(self, variable):
    cells = {'cell': self.findCells(1), 'source': self.symbols[variable], 'temp': self.findCells(1)}
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


