#!/usr/bin/env python
import re

from contextlib import contextmanager
from tokenizer import T_IDENT, T_COMPARE, T_OP, T_STRING, T_NUMBER, T_CHAR

class ExpectedException(BaseException):
  def __init__(self, expected):
    self.expected = expected
    self.token = self.tokens[0]
    self.remaining = ''.join([x.getString() for x in self.tokens])[:50]

  def __str__(self):
    return "Expected %s, got %s(%s) near %s" % (self.expected, self.token.__class__.__name__, self.token.getString(), self.remaining)

class Parser(object):
  opcodes = []
  tokens = []

  def __init__(self, tokens):
    self.tokens = list(tokens)

  def pop(self):
    return self.tokens.pop(0)

  def expect(self ,cls, val=None):
    if not isinstance(self.tokens[0], cls):
      raise ExpectedException("%s(%s)" % (cls.__name__, val))
    if val is not None:
      if self.tokens[0].getString() != val:
        raise ExpectedException(val)
    self.pop()


  def isa(self ,cls, val=None):
    if not isinstance(self.tokens[0], cls): return False
    if val is None: return True
    return self.tokens[0].getString() == val

  def do(self ,op, *params):
    self.opcodes.append((op, params))

  def value(self):
    token = self.tokens[0]

    if self.isa(T_NUMBER):
      self.do("PUSH", token.getValue())
      self.pop()
    elif self.isa(T_CHAR):
      self.do("PUSH", ord(token.getChar()))
      self.pop()
    elif self.isa(T_IDENT):
      self.do("GET", token.getString())
      self.pop()
    else:
      raise ExpectedException("value")

  def expression(self):
    self.value()

    token = self.tokens[0]
    if self.isa(T_COMPARE):
      self.pop()
      self.expression()
      self.do("COMPARE", token.getString())
    elif self.isa(T_OP, '+'):
      self.pop()
      self.expression()
      self.do("ADD")
    elif self.isa(T_OP, '-'):
      self.pop()
      self.expression()
      self.do("SUB")

  def statement(self):
    token = self.tokens[0]
    if self.isa(T_IDENT, "for"):
      self.pop()
      self.expect(T_OP, '(')
      self.statement()
      self.expect(T_OP, ';')
      # Capture expression opcodes
      oldOpcodes, self.opcodes = self.opcodes, []
      self.expression()
      expressionOpcodes, self.opcodes = self.opcodes, oldOpcodes

      self.expect(T_OP, ';')

      # Capture any opcodes
      oldOpcodes, self.opcodes = self.opcodes, []
      self.statement()
      statementOpcodes, self.opcodes = self.opcodes, oldOpcodes

      self.expect(T_OP, ')')
      self.expect(T_OP, '{')

      self.opcodes.extend(expressionOpcodes)

      self.do("FOR_OPEN")
      self.block()
      self.opcodes.extend(statementOpcodes)

      self.expect(T_OP, '}')

      self.do("FOR_CLOSE")
      self.opcodes.extend(expressionOpcodes)
      self.do("FOR_END")
    elif self.isa(T_IDENT, "if"):
      self.pop()
      self.expect(T_OP, '(')
      self.expression()
      self.expect(T_OP, ')')
      self.expect(T_OP, '{')
      self.do("IF_BEGIN")
      self.block()
      self.expect(T_OP, '}')

      self.do("IF_ELSE")
      if self.isa(T_IDENT, "else"):
        self.pop();
        self.expect(T_OP, '{')
        self.block()
        self.expect(T_OP, '}')

      self.do("IF_END")

    elif self.isa(T_IDENT):
      self.pop()
      if self.isa(T_OP, '--') or self.isa(T_OP, '++'):
        incrToken = self.pop()
        self.do("GET", token.getString())
        self.do("PUSH", 1)
        self.do("SUB" if incrToken.getString() == '--' else "ADD")
        self.do("SET", token.getString())
      elif self.isa(T_OP, '='):
        self.pop()
        self.expression()
        self.do("SET", token.getString())
      elif self.isa(T_OP, '('):
        self.pop()
        if token.getString() in ('print', 'println') and self.isa(T_STRING):
          self.do(token.getString().upper(), self.pop().getValue())
        else:
          args = 1
          self.expression()
          while self.isa(T_OP, ','):
            self.pop()
            self.expression()
            args += 1
          self.do("CALL", token.getString(), args)
        self.expect(T_OP, ')')

      else:
        raise ExpectedException("=, (, or comparison")

    else:
      raise ExpectedException("identifier")

  def block(self):
    while self.tokens and not self.isa(T_OP, '}'):
      if self.isa(T_OP, ';'):
        self.pop()
        continue
      self.statement()

  def parse(self):
    self.block()
    return self.opcodes


