"""
Pure Synchronous MTProto 2.0 Encrypted Sender.
Sends and receives encrypted Telegram RPC requests over blocking TCP sockets.
"""

import io
import time
from typing import Any, Optional

from ..crypto import AuthKey
from ..errors import (
    BadMessageError,
    BadServerSaltError,
    rpc_message_to_error,
)
from ..extensions import BinaryReader
from ..tl.core import GzipPacked, MessageContainer, RpcResult
from ..tl.types import BadMsgNotification, BadServerSalt
from .connection import SyncTcpIntermediateConnection
from .mtprotostate import MTProtoState


class SyncMTProtoSender:
    """
    100% Pure Synchronous MTProto Sender.
    Encrypted communication with Telegram servers without any asyncio event loop.
    """

    def __init__(self, connection: SyncTcpIntermediateConnection, auth_key: AuthKey):
        self.connection = connection
        self.auth_key = auth_key
        self.state = MTProtoState(auth_key=auth_key)

    def send(self, request: Any, max_retries: int = 5) -> Any:
        """
        Send an MTProto RPC request synchronously and return the decoded response.

        :param request: TLRequest instance
        :param max_retries: Number of retries on BadServerSalt or reconnects
        :return: Deserialized Telegram TLObject response
        """
        for attempt in range(max_retries):
            try:
                if not self.connection.is_connected:
                    self.connection.connect()

                # 1. Serialize request into buffer
                buf = io.BytesIO()
                msg_id = self.state.write_data_as_message(buf, bytes(request), content_related=True)
                payload = buf.getvalue()

                # 2. Encrypt using MTProto 2.0
                encrypted_data = self.state.encrypt_message_data(payload)

                # 3. Send over blocking socket
                self.connection.send(encrypted_data)

                # 4. Wait for matching RPC response
                result = self._receive_response(msg_id, request)
                return result

            except BadServerSaltError as e:
                self.state.salt = e.new_server_salt
                continue
            except BadMessageError as e:
                if e.code in (16, 17):
                    # Time offset error, retry with updated time offset
                    continue
                raise e
            except (ConnectionError, ConnectionResetError, TimeoutError) as e:
                self.connection.close()
                if attempt == max_retries - 1:
                    raise ConnectionError(f"Failed to communicate with Telegram: {e}") from e
                time.sleep(0.5)

        raise TimeoutError("Exceeded maximum retries waiting for Telegram response")

    def _receive_response(self, target_msg_id: int, request: Any) -> Any:
        """Read packets until the RPC response for target_msg_id is found."""
        start_time = time.time()
        timeout = self.connection.timeout

        while time.time() - start_time < timeout:
            raw_packet = self.connection.recv()
            tl_message = self.state.decrypt_message_data(raw_packet)

            res = self._process_message(tl_message.obj, target_msg_id, request)
            if res is not None:
                return res

        raise TimeoutError(f"Timed out waiting for response to message ID {target_msg_id}")

    def _process_message(self, obj: Any, target_msg_id: int, request: Any) -> Optional[Any]:
        """Process an unpacked TL message object."""
        if isinstance(obj, MessageContainer):
            for inner in obj.messages:
                res = self._process_message(inner.obj, target_msg_id, request)
                if res is not None:
                    return res
            return None

        if isinstance(obj, GzipPacked):
            with BinaryReader(obj.data) as reader:
                unpacked = reader.tgread_object()
                return self._process_message(unpacked, target_msg_id, request)

        if isinstance(obj, RpcResult):
            if obj.req_msg_id == target_msg_id:
                if obj.error:
                    error = rpc_message_to_error(obj.error, request)
                    raise error
                with BinaryReader(obj.body) as reader:
                    return request.read_result(reader)
            return None

        if isinstance(obj, BadServerSalt):
            self.state.salt = obj.new_server_salt
            if obj.bad_msg_id == target_msg_id:
                raise BadServerSaltError(obj.bad_msg_id, obj.new_server_salt)

        if isinstance(obj, BadMsgNotification):
            if obj.bad_msg_id == target_msg_id:
                # Error code 16 or 17 -> msg_id too low/high, adjust time offset
                if obj.error_code in (16, 17):
                    # Time offset correction
                    self.state.time_offset += 30
                raise BadMessageError(request, obj.error_code)

        return None
