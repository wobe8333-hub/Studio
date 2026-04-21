"""Phase 승격 이벤트를 data/global/notifications/ 에 기록한다."""
import uuid
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from src.core.ssot import read_json, write_json

_NOTIFICATIONS_FILE = "notifications.json"


def record_phase_promotion(
    notifications_dir: Path,
    channel_id: str,
    from_stage: str,
    to_stage: str,
) -> None:
    """Phase 승격 알림을 notifications.json 에 추가한다."""
    notifications_dir.mkdir(parents=True, exist_ok=True)
    notif_path = notifications_dir / _NOTIFICATIONS_FILE

    notifications = read_json(notif_path) if notif_path.exists() else []
    if not isinstance(notifications, list):
        notifications = []

    entry = {
        "id": str(uuid.uuid4()),
        "type": "phase_promotion",
        "channel_id": channel_id,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "read": False,
    }
    notifications.append(entry)
    write_json(notif_path, notifications)
    logger.info(f"[Notifier] Phase 승격 알림 기록: {channel_id} {from_stage} → {to_stage}")


def get_unread_notifications(notifications_dir: Path) -> list:
    """읽지 않은 알림 목록을 반환한다."""
    notif_path = notifications_dir / _NOTIFICATIONS_FILE
    if not notif_path.exists():
        return []
    notifications = read_json(notif_path)
    if not isinstance(notifications, list):
        return []
    return [n for n in notifications if not n.get("read", False)]
