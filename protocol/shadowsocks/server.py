#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: booopooob@gmail.com
# 
# Info: asyncio  - Stream <https://docs.python.org/3/library/asyncio-stream.html#asyncio-tcp-echo-server-streams>
#                - Transport <https://docs.python.org/3/library/asyncio-protocol.html>
#                - relay in data_received: https://stackoverflow.com/questions/21295068/how-can-i-create-a-relay-server-using-tulip-asyncio-in-python/21297354#21297354
#
import asyncio
from argparse import Namespace

import functools
import settings
from packet.stream_packer import StreamPacker
from protocol.COMMON.client_relay_protocal import SimpleClientRelayProtocol
from protocol.COMMON.server_relay_protocal import ServerRelayProtocol
from protocol.shadowsocks.encoder import ShadowsocksEncryptionWrapperEncoder
from protocol.shadowsocks.header import ShadowsocksPacketHeader


class ShadowsocksServerRelayProtocol(ServerRelayProtocol):
    def __init__(self, loop, config: Namespace = None):
        super(ShadowsocksServerRelayProtocol, self).__init__(loop, config)
        self.header = None
        self.stream_packer = StreamPacker()

    def create_encoder(self):
        return ShadowsocksEncryptionWrapperEncoder(
            encrypt_method=self.config.cipher_method,
            password=self.config.password,
            encript_mode=True)

    def create_decoder(self):
        return ShadowsocksEncryptionWrapperEncoder(
            encrypt_method=self.config.cipher_method,
            password=self.config.password,
            encript_mode=False)

    def get_relay_protocal(self):
        return SimpleClientRelayProtocol(functools.partial(self.data_received_from_remote),
                                         self.connection_lost_from_remote)

    def data_received(self, data):
        if self.decoder:
            data = self.decoder.decode(data)

        if not self.header:
            self.header, data = self.stream_packer.unpack(header=ShadowsocksPacketHeader(), data=data)
            if not self.header:
                return
        else:
            _, data = self.stream_packer.unpack(header=None, data=data)
            if not data:
                return

        if self.client:
            # TODO: inspect the relay client' connection status, try to reconnect if disconn
            asyncio.ensure_future(self.send_data_to_remote(data), loop=self.loop)
        else:
            # TODO: run two task one by one, using the simplier style
            f = asyncio.ensure_future(self.set_up_relay(self.header.addr, self.header.port), loop=self.loop)

            def send_data(_):
                asyncio.ensure_future(self.send_data_to_remote(data), loop=self.loop)

            f.add_done_callback(send_data)


if __name__ == '__main__':
    pass