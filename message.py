# -*- encoding=utf8 -*-
from notify import send


class message(object):
    """消息推送类"""

    def send(self, desp='', isOrder=False):
        self.sendAny(desp)

    def sendAny(self, desp=''):
        print(desp)
        send("京东商品监控", desp)
