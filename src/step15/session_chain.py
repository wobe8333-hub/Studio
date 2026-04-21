"""STEP 15 — 세션 체인 엔진."""
from loguru import logger

from src.core.config import KNOWLEDGE_DIR
from src.core.ssot import now_iso, write_json


def build_series_chain(channel_id: str, base_topic: str, episode_count: int = 3) -> dict:
    chain_dir = KNOWLEDGE_DIR/channel_id/"series"; chain_dir.mkdir(parents=True, exist_ok=True)
    suffixes  = ["기초편","심화편","실전편"]
    episodes  = [{"episode":i+1,"title":f"{base_topic} {suffixes[i]}",
                   "channel_id":channel_id,"is_trending":False,"topic_type":"series",
                   "series_ref":base_topic,"created_at":now_iso()}
                 for i in range(min(episode_count,len(suffixes)))]
    chain = {"schema_version":"1.0","channel_id":channel_id,"base_topic":base_topic,
              "episode_count":len(episodes),"episodes":episodes,"created_at":now_iso()}
    write_json(chain_dir/f"series_{base_topic[:20].replace(' ','_')}.json", chain)
    logger.info(f"[STEP15] {channel_id} 시리즈: {base_topic} ({len(episodes)}편)")
    return chain
