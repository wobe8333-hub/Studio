"""STEP 08 오케스트레이터.
버그 수정(BUG-3): RUNS_DIR, BGM_DIR dead import 제거.
버그 수정(BUG-4): GEMINI_API_KEY, GEMINI_TEXT_MODEL 이중 import 제거.
"""
import time, logging, shutil
from src.core.ssot import (write_json, read_json, json_exists,
                            sha256_file, now_iso, get_run_dir)
from src.core.config import CHANNELS_DIR
from src.core.decision_trace import append_trace
from src.step08.script_generator import generate_script
from src.step08.image_generator import generate_batch as gen_images
from src.step08.manim_generator import generate_and_run as manim_run
from src.step08.narration_generator import generate_narration
from src.step08.subtitle_generator import generate_subtitles
from src.step08.ffmpeg_composer import (image_to_clip, concat_clips,
                                         add_narration, add_subtitles)

logger = logging.getLogger(__name__)

def run_step08(channel_id: str, topic: dict, style_policy: dict,
               revenue_policy: dict, algorithm_policy: dict) -> str:
    import google.generativeai as genai
    from src.core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL
    from src.quota.gemini_quota import throttle_if_needed, record_request

    run_id = f"run_{channel_id}_{int(time.time())}"
    run_dir= get_run_dir(channel_id, run_id)
    s08    = run_dir / "step08"
    clips_g= s08/"clips"/"gemini"; clips_m=s08/"clips"/"manim"
    imgs_ai= s08/"images"/"assets_ai"; imgs_kf=s08/"images"/"keyframes"

    for d in [s08,clips_g,clips_m,imgs_ai,imgs_kf]:
        d.mkdir(parents=True, exist_ok=True)

    write_json(run_dir/"manifest.json", {
        "run_id":run_id,"channel_id":channel_id,"schema_version":"1.0",
        "run_state":"RUNNING","created_at":now_iso(),"topic":topic,
    })
    write_json(run_dir/"decision_trace.json", {"events":[]})
    write_json(run_dir/"observability.json",  {"run_id":run_id,"start":now_iso()})
    write_json(run_dir/"reflection.json",     {"run_id":run_id})
    write_json(run_dir/"cost.json", {
        "channel_id":channel_id,"run_id":run_id,
        "cost_recorded_at":now_iso(),"gemini_api":{"total_krw":0.0},"total_cost_krw":0.0,
    })

    logger.info(f"[STEP08] {channel_id}/{run_id} script 생성...")
    script   = generate_script(channel_id, run_id, topic, style_policy, revenue_policy, algorithm_policy)
    write_json(s08/"script.json", script)

    sections = script.get("sections",[])
    m_secs   = [s for s in sections if s.get("render_tool")=="manim"]
    g_secs   = [s for s in sections if s.get("render_tool")!="manim"]
    clip_paths=[]; fb_cnt=0

    img_res = gen_images(g_secs, imgs_ai)
    for sec in g_secs:
        ip = img_res.get(sec["id"])
        if ip and ip.exists():
            cp = clips_g/f"section_{sec['id']:03d}.mp4"
            image_to_clip(ip, cp, duration_sec=6.0)
            if cp.exists(): clip_paths.append((sec["id"], cp))

    stab_log = []
    for sec in m_secs:
        ok, cp, fb = manim_run(sec, clips_m)
        if ok and cp:
            clip_paths.append((sec["id"], cp))
            stab_log.append({"section_id":sec["id"],"success":True})
        else:
            fb_cnt += 1
            stab_log.append({"section_id":sec["id"],"success":False})
            from src.step08.image_generator import generate_single_image
            fp = imgs_ai/f"section_{sec['id']:03d}_fallback.png"
            generate_single_image(sec.get("animation_prompt",""), fp)
            if fp.exists():
                cfp = clips_g/f"section_{sec['id']:03d}_fallback.mp4"
                image_to_clip(fp, cfp, duration_sec=6.0)
                if cfp.exists(): clip_paths.append((sec["id"], cfp))

    fb_rate = fb_cnt / max(len(m_secs),1)
    write_json(s08/"manim_stability_report.json", {
        "run_id":run_id,"manim_sections_attempted":len(m_secs),
        "manim_sections_success":len(m_secs)-fb_cnt,
        "manim_sections_fallback":fb_cnt,"fallback_rate":round(fb_rate,3),
        "hitl_required":fb_rate>0.50,"details":stab_log,
    })
    if fb_rate > 0.50:
        append_trace(run_dir/"decision_trace.json","MANIM_HITL",{"fallback_rate":fb_rate})

    clip_paths.sort(key=lambda x:x[0])
    ordered = [p for _,p in clip_paths]
    if not ordered: raise RuntimeError("STEP08_FAIL: 클립 없음")

    concat_path = s08/"video_raw.mp4"
    concat_clips(ordered, concat_path)
    narr_path = s08/"narration.wav"
    generate_narration(script, narr_path)
    with_narr = s08/"video_narr.mp4"
    add_narration(concat_path, narr_path, with_narr)
    srt_path  = s08/"subtitles.srt"
    generate_subtitles(script, narr_path, srt_path)
    with_subs = s08/"video_subs.mp4"
    add_subtitles(with_narr, srt_path, with_subs)
    shutil.copy2(with_subs, s08/"video.mp4")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
    tc    = script.get("title_candidates",[topic.get("reinterpreted_title","제목 없음")])
    write_json(s08/"title.json", {"title_candidates":tc,"selected":tc[0] if tc else ""})
    seo   = script.get("seo",{})
    desc  = (f"{seo.get('description_first_2lines','')}\n\n"
             f"{script.get('affiliate_insert',{}).get('text','')}\n\n"
             f"{script.get('financial_disclaimer','') or script.get('medical_disclaimer','') or ''}\n\n"
             f"{script.get('ai_label','이 영상은 AI가 제작에 참여했습니다.')}")
    (s08/"description.txt").write_text(desc, encoding="utf-8")
    throttle_if_needed(); record_request()
    tag_r = model.generate_content(
        f"YouTube 태그 15개 콤마 구분. 주제: {topic.get('reinterpreted_title','')}",
        generation_config=genai.GenerationConfig(max_output_tokens=200),
    )
    write_json(s08/"tags.json", {"tags":[t.strip() for t in tag_r.text.split(",")][:15]})
    write_json(s08/"render_report.json", {
        "run_id":run_id,"channel_id":channel_id,
        "render_completed_at":now_iso(),"bgm_used":False,
        "video_spec":script.get("video_spec",{}),"target_duration_sec":script.get("target_duration_sec",720),
        "sections_count":len(sections),"manim_sections":len(m_secs),
    })
    sp = CHANNELS_DIR/channel_id/"style_policy_master.json"
    if sp.exists(): shutil.copy2(sp, s08/"style_policy.json")

    hashes = {}
    for fn in ["script.json","narration.wav","subtitles.srt","video.mp4","render_report.json"]:
        fp = s08/fn
        if fp.exists(): hashes[fn] = sha256_file(fp)
    write_json(s08/"artifact_hashes.json", hashes)

    mf = read_json(run_dir/"manifest.json")
    mf.update({"run_state":"COMPLETED","completed_at":now_iso()})
    write_json(run_dir/"manifest.json", mf)

    logger.info(f"[STEP08] {channel_id}/{run_id} 완료")
    return run_id
