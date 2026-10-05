"""
Update State Tracking and Gap Recovery Engine for Telegram.
Tracks pts, qts, date, seq and recovers missed updates via getDifference.
100% Pure Synchronous, Zero Asyncio.
"""

from dataclasses import dataclass
from typing import Optional, List, Any
from .tl import functions, types
from .utils import get_input_channel


@dataclass
class UpdateSyncState:
    pts: int
    qts: int
    date: int
    seq: int
    unread_count: int = 0


class SyncUpdateEngine:
    """
    Manages Telegram state synchronization and update gap recovery.
    """

    def __init__(self, client: Any):
        self.client = client
        self.state: Optional[UpdateSyncState] = None

    def get_state(self) -> UpdateSyncState:
        """
        Fetch current account state parameters (pts, qts, date, seq).
        """
        res = self.client._invoke(functions.updates.GetStateRequest())
        self.state = UpdateSyncState(
            pts=res.pts,
            qts=res.qts,
            date=res.date,
            seq=res.seq,
            unread_count=getattr(res, 'unread_count', 0)
        )
        return self.state

    def get_difference(
        self,
        pts: Optional[int] = None,
        date: Optional[int] = None,
        qts: Optional[int] = None,
        pts_total_limit: Optional[int] = None
    ) -> Any:
        """
        Get missed messages and updates since the given pts/date/qts state.
        """
        current_pts = pts if pts is not None else (self.state.pts if self.state else 1)
        current_date = date if date is not None else (self.state.date if self.state else 0)
        current_qts = qts if qts is not None else (self.state.qts if self.state else 0)

        req = functions.updates.GetDifferenceRequest(
            pts=current_pts,
            date=current_date,
            qts=current_qts,
            pts_total_limit=pts_total_limit
        )
        result = self.client._invoke(req)

        # Update cached state if difference returned state updates
        if hasattr(result, 'state'):
            st = result.state
            self.state = UpdateSyncState(
                pts=st.pts,
                qts=st.qts,
                date=st.date,
                seq=st.seq,
                unread_count=getattr(st, 'unread_count', 0)
            )
        elif hasattr(result, 'intermediate_state'):
            st = result.intermediate_state
            self.state = UpdateSyncState(
                pts=st.pts,
                qts=st.qts,
                date=st.date,
                seq=st.seq,
                unread_count=getattr(st, 'unread_count', 0)
            )

        return result

    def get_channel_difference(
        self,
        channel: Any,
        pts: int,
        limit: int = 100,
        filter: Optional[Any] = None
    ) -> Any:
        """
        Get missed messages and updates for a specific channel since the given pts.
        """
        input_channel = get_input_channel(self.client.get_input_entity(channel))
        req = functions.updates.GetChannelDifferenceRequest(
            channel=input_channel,
            filter=filter or types.ChannelMessagesFilterEmpty(),
            pts=pts,
            limit=limit,
            force=False
        )
        return self.client._invoke(req)
