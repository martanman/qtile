# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import sys
from base import Layout
from .. import command, utils


class _WinStack(object):
    split = False
    _current = 0
    def _getCurrent(self):
        return self._current

    def _setCurrent(self, x):
        if len(self):
            self._current = abs(x%len(self))
        else:
            self._current = 0

    current = property(_getCurrent, _setCurrent)

    @property
    def cw(self):
        if not self.lst:
            return None
        return self.lst[self.current]

    def __init__(self):
        self.lst = []

    def toggleSplit(self):
        self.split = False if self.split else True

    def join(self, ws):
        # FIXME: This buggers up window order - windows should be injected BEFORE
        # the current offset.
        self.lst.extend(ws.lst)

    def focus(self, w):
        self.current = self.lst.index(w)

    def add(self, w):
        self.lst.insert(self.current, w)

    def remove(self, w):
        idx = self.lst.index(w)
        self.lst.remove(w)
        if idx > self.current:
            self.current -= 1
        else:
            # This apparently nonsensical assignment caps the value using the
            # property definition.
            self.current = self.current

    def index(self, c):
        return self.lst.index(c)

    def __len__(self):
        return len(self.lst)

    def __getitem__(self, i):
        return self.lst[i]

    def __contains__(self, x):
        return x in self.lst

    def __repr__(self):
        return "_WinStack(%s, %s)"%(self.current, str([i.name for i in self]))

    def info(self):
        return dict(
            windows = [i.name for i in self],
            split = self.split,
            current = self.current,
        )


class Stack(Layout):
    name = "stack"
    defaults = dict(
        border_focus = "#0000ff",
        border_normal = "#000000",
        border_width = 1
    )
    def __init__(self, stacks=2, **attrs):
        """
            :stacks Number of stacks to start with.
        """
        Layout.__init__(self, **attrs)
        self.stacks = [_WinStack() for i in range(stacks)]

    @property
    def currentStack(self):
        return self.stacks[self.currentStackOffset]

    @property
    def currentStackOffset(self):
        for i, s in enumerate(self.stacks):
            if self.group.currentWindow in s:
                return i
        return 0

    def clone(self, group):
        c = Layout.clone(self, group)
        # These are mutable
        c.stacks = [_WinStack() for i in self.stacks]
        return c

    def _findNext(self, lst, offset):
        for i in lst[offset+1:]:
            if i:
                return i
        else:
            for i in lst[:offset]:
                if i:
                    return i

    def deleteCurrentStack(self):
        if len(self.stacks) > 1:
            off = self.currentStackOffset or 0
            s = self.stacks[off]
            self.stacks.remove(s)
            off = min(off, len(self.stacks)-1)
            self.stacks[off].join(s)
            if self.stacks[off]:
                self.group.focus(
                    self.stacks[off].cw,
                    False
                )

    def nextStack(self):
        n = self._findNext(
                self.stacks,
                self.currentStackOffset
            )
        if n:
            self.group.focus(n.cw, True)

    def previousStack(self):
        n = self._findNext(
                list(reversed(self.stacks)),
                len(self.stacks) - self.currentStackOffset - 1
            )
        if n:
            self.group.focus(n.cw, True)

    def focus(self, c):
        for i in self.stacks:
            if c in i:
                i.focus(c)

    def add(self, c):
        for i in self.stacks:
            if not i:
                i.add(c)
                return
        self.currentStack.add(c)

    def remove(self, c):
        currentOffset = self.currentStackOffset
        for i in self.stacks:
            if c in i:
                i.remove(c)
                break
        if self.stacks[currentOffset].cw:
            return self.stacks[currentOffset].cw
        else:
            n = self._findNext(
                    list(reversed(self.stacks)),
                    len(self.stacks) - currentOffset - 1
                )
            if n:
                return n.cw

    def configure(self, c):
        for i, s in enumerate(self.stacks):
            if c in s:
                break
        else:
            c.hide()

        if c is self.group.currentWindow:
            px = self.group.qtile.colorPixel(self.border_focus)
        else:
            px = self.group.qtile.colorPixel(self.border_normal)

        columnWidth = int(self.group.screen.dwidth/float(len(self.stacks)))
        xoffset = self.group.screen.dx + i*columnWidth
        winWidth = columnWidth - 2*self.border_width

        if s.split:
            columnHeight = int(self.group.screen.dheight/float(len(s)))
            winHeight = columnHeight - 2*self.border_width
            yoffset = self.group.screen.dy + s.index(c)*columnHeight
            c.place(
                xoffset,
                yoffset,
                winWidth,
                winHeight,
                self.border_width,
                px
            )
            c.unhide()
        else:
            if c == s.cw:
                c.place(
                    xoffset,
                    self.group.screen.dy,
                    winWidth,
                    self.group.screen.dheight - 2*self.border_width,
                    self.border_width,
                    px
                )
                c.unhide()
            else:
                c.hide()

    def info(self):
        d = Layout.info(self)
        d["stacks"] = [i.info() for i in self.stacks]
        d["current_stack"] = self.currentStackOffset
        return d

    def cmd_toggle_split(self):
        """
            Toggle vertical split on the current layout.
        """
        self.currentStack.toggleSplit()
        self.group.layoutAll()

    def cmd_down(self):
        """
            Switch to the next window in this stack.
        """
        self.currentStack.current -= 1
        self.group.focus(self.currentStack.cw, False)

    def cmd_up(self):
        """
            Switch to the previous window in this stack.
        """
        self.currentStack.current += 1
        self.group.focus(self.currentStack.cw, False)

    def cmd_shuffle_up(self):
        """
            Shuffle the order of this stack up.
        """
        utils.shuffleUp(self.currentStack.lst)
        self.currentStack.current += 1
        self.group.layoutAll()

    def cmd_shuffle_down(self):
        """
            Shuffle the order of this stack down.
        """
        utils.shuffleDown(self.currentStack.lst)
        self.currentStack.current -= 1
        self.group.layoutAll()

    def cmd_delete(self):
        """
            Delete the current stack from the layout.
        """
        self.deleteCurrentStack()

    def cmd_add(self):
        """
            Add a stack to the layout.
        """
        self.stacks.append(_WinStack())
        self.group.layoutAll()

    def cmd_rotate(self):
        """
            Rotate order of the stacks.
        """
        utils.shuffleUp(self.stacks)
        self.group.layoutAll()

    def cmd_next(self):
        """
            Focus next stack.
        """
        return self.nextStack()

    def cmd_previous(self):
        """
            Focus previous stack.
        """
        return self.previousStack()

    def cmd_client_to_next(self):
        """
            Send the current client to the next stack.
        """
        return self.cmd_client_to_stack(self.currentStackOffset + 1)

    def cmd_client_to_previous(self):
        """
            Send the current client to the previous stack.
        """
        return self.cmd_client_to_stack(self.currentStackOffset - 1)

    def cmd_client_to_stack(self, n):
        """
            Send the current client to stack n, where n is an integer offset.
            If is too large or less than 0, it is wrapped modulo the number of
            stacks.
        """
        if not self.currentStack:
            return
        next = n%len(self.stacks)
        win = self.currentStack.cw
        self.currentStack.remove(win)
        self.stacks[next].add(win)
        self.stacks[next].focus(win)

