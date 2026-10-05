"""Pure Synchronous MTProto Plain Sender for unencrypted initial handshake."""

import struct
from .mtprotostate import MTProtoState
from ..errors import InvalidBufferError
from ..extensions import BinaryReader


class SyncMTProtoPlainSender:
    """Sends unencrypted plain MTProto requests synchronously."""

    def __init__(self, connection):
        self._state = MTProtoState(auth_key=None)
        self._connection = connection

    def send(self, request):
        """Send plain request and wait for reply synchronously."""
        body = bytes(request)
        msg_id = self._state._get_new_msg_id()
        self._connection.send(
            struct.pack('<qqi', 0, msg_id, len(body)) + body
        )

        resp_body = self._connection.recv()
        if len(resp_body) < 8:
            raise InvalidBufferError(resp_body)

        with BinaryReader(resp_body) as reader:
            auth_key_id = reader.read_long()
            assert auth_key_id == 0, 'Bad auth_key_id'

            msg_id = reader.read_long()
            assert msg_id != 0, 'Bad msg_id'

            length = reader.read_int()
            assert length > 0, 'Bad length'
            return reader.tgread_object()
