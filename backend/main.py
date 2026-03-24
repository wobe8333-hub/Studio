"""
FastAPI 엔트리포인트 - AI Animation Studio Backend
"""

from dotenv import load_dotenv
from pathlib import Path

# 절대경로 기반 .env 로딩
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

import os
import sys
import asyncio
import hashlib
import json
import uuid
import traceback
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Dict, Optional, Literal, Any

# UTF-8 런타임 강제 설정 (애플리케이션 시작 시)
def _force_utf8_runtime():
    """Python 런타임 UTF-8 강제 설정"""
    # PYTHONUTF8 환경변수 설정
    if "PYTHONUTF8" not in os.environ:
        os.environ["PYTHONUTF8"] = "1"
    
    # stdout/stderr 인코딩 재설정 (가능할 때)
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        # reconfigure가 지원되지 않는 경우 무시
        pass

# 애플리케이션 시작 시 UTF-8 강제
_force_utf8_runtime()

# 데이터베이스 초기화
from backend.db.database import (
    init_db,
    create_learning_entry,
    get_all_concepts_from_recent_entries,
    create_job,
    update_job_status,
    get_job,
)
from backend.ai_engine.learning_engine import learn_from_text
from backend.ai_engine.topic_recommender import recommend_topics
from backend.ai_engine.longform_structure_extractor import (
    analyze_template_structure,
    save_analysis_result,
    load_latest_analysis,
)
from backend.ai_engine.longform_scene_splitter import (
    split_script_to_scenes,
    load_style_profile,
    save_video_plan,
    load_video_plan,
)
try:
    from backend.ai_engine.longform_scene_splitter import _generate_shot_prompt
except ImportError:
    # _generate_shot_prompt가 export되지 않은 경우를 위한 fallback
    _generate_shot_prompt = None
from backend.video.premium_renderer import render_premium_video
from backend.video.utils import (
    probe_video_metadata,
    make_cache_key,
    has_final_cache,
    save_final_cache,
    cleanup_output_root,
)
from backend.schemas.longform_scene_v1 import VideoPlanV1
from backend.video.longform_renderer import render_longform_video
from backend.utils.run_manager import append_decision_trace, load_run_manifest
from backend.utils.observability import write_event, update_metrics, ensure_metrics
from backend.core.sample_inputs import (
    SAMPLE_WORD,
    SAMPLE_SENTENCE,
    SAMPLE_PARAGRAPH,
    STEP2_TEXT,
    STEP2_TOPIC,
    get_step2_example
)

# FastAPI 앱 생성
app = FastAPI(title="AI Animation Studio API", version="1.0.0")


def inject_checkprompts_examples(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    OpenAPI 스키마에 checkprompts 예시 자동 주입 (v6-Step14)
    
    Args:
        schema: OpenAPI 스키마
    
    Returns:
        Dict: 예시가 주입된 OpenAPI 스키마
    """
    try:
        checkprompts_dir = Path(__file__).resolve().parent / "checkprompts"
        examples_v6_path = checkprompts_dir / "examples.v6.json"
        
        if not examples_v6_path.exists():
            return schema
        
        with open(examples_v6_path, "r", encoding="utf-8") as f:
            examples_v6 = json.load(f)
        
        paths = schema.get("paths", {})
        
        # examples.v6.json의 각 경로에 예시 주입
        for path, path_spec in examples_v6.items():
            if path not in paths:
                continue
            
            method_spec = path_spec.get("post") or path_spec.get("get")
            if not method_spec:
                continue
            
            method = "post" if path_spec.get("post") else "get"
            endpoint_spec = paths[path].get(method, {})
            request_body = endpoint_spec.get("requestBody", {})
            content = request_body.get("content", {})
            json_content = content.get("application/json", {})
            
            if not json_content:
                continue
            
            # examples 주입
            example_value = method_spec.get("value", {})
            if example_value:
                json_content["examples"] = {
                    "v6_default": {
                        "summary": method_spec.get("summary", "v6 default example"),
                        "value": example_value
                    }
                }
        
    except Exception:
        # 예시 주입 실패는 무시 (기존 스키마 유지)
        pass
    
    return schema


# OpenAPI 스키마 커스터마이즈
original_openapi = app.openapi

def custom_openapi():
    """OpenAPI 스키마 커스터마이즈 (checkprompts 예시 주입)"""
    if app.openapi_schema:
        return app.openapi_schema
    
    schema = original_openapi()
    schema = inject_checkprompts_examples(schema)
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi

# 정적 파일 서빙 (output 폴더)
output_dir = Path(__file__).resolve().parent / "output"
output_dir.mkdir(exist_ok=True)
app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

# 정적 파일 서빙 (static 폴더 - 프론트엔드)
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 정적 파일 서빙 (assets 폴더 - 이미지 에셋)
assets_dir = Path(__file__).resolve().parent / "assets"
assets_dir.mkdir(exist_ok=True)
app.mount("/static/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# Job 로그 디렉토리
logs_root = output_dir / "logs"
logs_root.mkdir(parents=True, exist_ok=True)

# Job 동시 실행 제한 (기본 1)
JOB_MAX_CONCURRENCY = int(os.getenv("JOB_MAX_CONCURRENCY", "1"))
job_semaphore = asyncio.Semaphore(JOB_MAX_CONCURRENCY)

# 데이터베이스 초기화
init_db()

# v3-Step5 Memory 조회 API 라우터 등록
from backend.api.routes.memory_v3 import router as memory_v3_router
app.include_router(memory_v3_router)


@app.on_event("startup")
async def startup_cleanup():
    """
    FastAPI 서버 시작 시 1회 output 디렉토리 정리 실행
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        output_root = backend_dir / "output"
        summary = cleanup_output_root(output_root)
        print(
            f"[CLEANUP_STARTUP] temp_deleted={summary['temp_deleted']} "
            f"final_deleted={summary['final_deleted']} "
            f"logs_deleted={summary['logs_deleted']}"
        )
    except Exception as e:
        print(f"[CLEANUP_STARTUP] error={e}")


# Request Models
class LearnTextRequest(BaseModel):
    text: str = Field(..., description="학습할 텍스트", examples=[SAMPLE_SENTENCE])
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "text": SAMPLE_PARAGRAPH
                }
            ]
        }
    )


class PremiumRenderRequest(BaseModel):
    render_mode: Literal["graphic", "sd"] = Field(
        "graphic",
        description="렌더링 모드: 'graphic' (그래픽 합성) 또는 'sd' (Stable Diffusion)",
        example="graphic"
    )
    scenes: List[Dict] = Field(
        ...,
        description="씬 리스트. render_mode에 따라 형식이 다릅니다:\n"
                   "- graphic: {scene_number, background: {color(optional)}, texts: {title, subtitle, body_lines[], cta}, character: {image, position, scale}, layout(optional), duration}\n"
                   "  * layout 없으면 자동 할당: 첫 씬=title_card, 중간=explain_card, 마지막=summary_card\n"
                   "  * background.color 없으면 팔레트에서 자동 선택\n"
                   "- sd: {scene_number, description, image_prompt, duration}",
        example=[
            {
                "scene_number": 1,
                "background": {},
                "texts": {
                    "title": "자영업자 폐업률",
                    "subtitle": "왜 이렇게 높을까?"
                },
                "character": {
                    "image": "owner_default.png",
                    "position": "right",
                    "scale": 0.6
                },
                "layout": "title_card",
                "duration": 4.0
            },
            {
                "scene_number": 2,
                "background": {},
                "texts": {
                    "body_lines": [
                        "2023년 기준 자영업자 폐업률은",
                        "전년 대비 15% 증가했습니다.",
                        "주요 원인은 임대료 상승과",
                        "경기 침체입니다."
                    ]
                },
                "character": {
                    "image": "owner_default.png",
                    "position": "right",
                    "scale": 0.6
                },
                "layout": "explain_card",
                "duration": 5.0
            },
            {
                "scene_number": 3,
                "background": {},
                "texts": {
                    "title": "정부 지원 정책 확인하기",
                    "cta": "더 알아보기"
                },
                "character": {
                    "image": "owner_default.png",
                    "position": "right",
                    "scale": 0.4
                },
                "layout": "summary_card",
                "duration": 3.0
            }
        ]
    )
    script_text: Optional[str] = Field(
        "",
        description="스크립트 텍스트 (TTS용)",
        examples=[SAMPLE_SENTENCE],
    )
    template_id: Optional[str] = Field(
        "simple_korean_2d_v1",
        description="사용할 템플릿 ID (스타일 식별자)",
        example="simple_korean_2d_v1",
    )
    template_version: Optional[str] = Field(
        "1.0.0",
        description="템플릿 버전",
        example="1.0.0",
    )


# Health Check
@app.get("/")
async def root():
    """Health check 엔드포인트"""
    return {"status": "ok"}


# Learning 엔드포인트
@app.post("/learn/text")
async def learn_text(request: LearnTextRequest = Body(..., example={"text": SAMPLE_PARAGRAPH})):
    """
    텍스트에서 학습하여 요약과 개념 추출
    
    Args:
        request: 학습할 텍스트
        
    Returns:
        학습 결과 (summary, concepts 포함)
    """
    try:
        # 학습 처리
        result = learn_from_text(request.text)
        
        # 데이터베이스에 저장
        entry = create_learning_entry(
            raw_text=request.text,
            summary=result["summary"],
            concepts=result["concepts"],
            source="api:text"
        )
        
        return {
            "success": True,
            "id": entry["id"],
            "summary": result["summary"],
            "concepts": result["concepts"],
            "created_at": entry["created_at"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"학습 처리 중 오류 발생: {str(e)}")


# Topic Recommendation 엔드포인트
@app.get("/recommend/topics")
async def get_recommended_topics(limit: int = Query(5, description="추천할 주제 수", example=5, ge=1, le=50)):
    """
    학습된 개념을 기반으로 주제 추천
    
    Args:
        limit: 추천할 주제 수 (기본값: 5, 최소 1, 최대 50)
        
    Returns:
        추천 주제 리스트
    """
    try:
        # 최근 학습 항목에서 concepts 수집
        concepts = get_all_concepts_from_recent_entries(limit=20)
        
        # 주제 추천 생성
        recommendations = recommend_topics(concepts, limit=limit)
        
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주제 추천 중 오류 발생: {str(e)}")


# Video Render 엔드포인트 (기본)
@app.post("/video/render")
async def render_video(request: Dict):
    """
    기본 비디오 렌더링 (구현 예정)
    
    Args:
        request: 렌더링 요청 데이터
        
    Returns:
        렌더링 결과
    """
    return {
        "status": "not_implemented",
        "message": "기본 비디오 렌더링은 아직 구현되지 않았습니다. /video/render/premium을 사용해주세요."
    }


# Premium Video Render 엔드포인트
@app.post("/video/render/premium")
async def render_premium(request: PremiumRenderRequest):
    """
    프리미엄 영상 생성 파이프라인
    
    두 가지 렌더링 모드를 지원합니다:
    - **graphic** (기본값): 그래픽 합성 기반. 캐릭터 PNG와 텍스트를 합성하여 영상 생성
    - **sd**: Stable Diffusion 기반. Replicate API를 사용하여 이미지 생성 후 영상 합성
    
    Args:
        request: 
            - render_mode: 렌더링 모드 ("graphic" 또는 "sd", 기본값: "graphic")
            - scenes: 씬 리스트
                - graphic 모드: {scene_number, background: {color}, texts: {title, subtitle}, character: {image, position}, layout, duration}
                - sd 모드: {scene_number, description, image_prompt, duration}
            - script_text: 스크립트 텍스트 (TTS용, 선택사항)
        
    Returns:
        생성된 비디오 파일 경로 및 URL
    """
    try:
        # 씬 데이터 기본 검증
        if not request.scenes:
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "error_code": "no_scenes",
                    "message": "scenes가 비어있습니다.",
                },
            )
        
        # scene_number 자동 채번 및 중복 검증
        seen_numbers = set()
        for idx, scene in enumerate(request.scenes):
            if "scene_number" not in scene or scene.get("scene_number") is None:
                scene["scene_number"] = idx + 1
            num = scene.get("scene_number")
            if num in seen_numbers:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "status": "error",
                        "error_code": "duplicate_scene_number",
                        "message": f"scene_number {num}이(가) 중복됩니다.",
                    },
                )
            seen_numbers.add(num)

        # render_mode에 따른 추가 검증
        if request.render_mode == "sd":
            # SD 모드: REPLICATE_API_TOKEN 확인 (422: Unprocessable Entity)
            replicate_token = os.getenv("REPLICATE_API_TOKEN")
            if not replicate_token:
                raise HTTPException(
                    status_code=422,
                    detail="SD 모드를 사용하려면 REPLICATE_API_TOKEN이 필요합니다. .env 파일에 REPLICATE_API_TOKEN을 설정해주세요."
                )
            
            # SD 씬 데이터 검증
            for i, scene in enumerate(request.scenes):
                if "scene_number" not in scene:
                    raise HTTPException(
                        status_code=422,
                        detail=f"씬 {i+1}에 scene_number가 없습니다."
                    )
                if "description" not in scene and "image_prompt" not in scene:
                    raise HTTPException(
                        status_code=422,
                        detail=f"씬 {i+1}에 description 또는 image_prompt가 없습니다."
                    )
        else:
            # Graphic 모드: 씬 데이터 검증
            for i, scene in enumerate(request.scenes):
                if "scene_number" not in scene:
                    raise HTTPException(
                        status_code=422,
                        detail=f"씬 {i+1}에 scene_number가 없습니다."
                    )
                if "background" not in scene:
                    raise HTTPException(
                        status_code=422,
                        detail=f"씬 {i+1}에 background가 없습니다. (graphic 모드 필수)"
                    )
                if "texts" not in scene:
                    raise HTTPException(
                        status_code=422,
                        detail=f"씬 {i+1}에 texts가 없습니다. (graphic 모드 필수)"
                    )
        
        # 출력 디렉토리 설정 (절대경로)
        backend_dir = Path(__file__).resolve().parent
        output_root = backend_dir / "output"
        videos_dir = output_root / "videos"

        # 캐시 키 생성 (renderer_type + scenes + assets_version)
        cache_key = make_cache_key(request.render_mode, request.scenes)

        # 1) final 캐시 히트 시: 렌더링 없이 복사 후 반환
        cached_final = has_final_cache(cache_key)
        cached_flag = False
        if cached_final is not None:
            # 새 job과 동일한 패턴을 맞추기 위해 final_<uuid>.mp4를 생성
            video_id = uuid.uuid4().hex
            final_video_path = output_root / f"final_{video_id}.mp4"
            final_video_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                # 캐시 파일을 최종 경로로 복사
                import shutil as _shutil
                _shutil.copy2(str(cached_final), str(final_video_path))
                cached_flag = True
                video_path = str(final_video_path)
            except Exception:
                # 캐시 복사 실패 시 캐시를 무시하고 새로 렌더링
                cached_flag = False
                video_path = render_premium_video(
                    scenes=request.scenes,
                    script_text=request.script_text or "",
                    output_dir=str(videos_dir),
                    render_mode=request.render_mode,
                )
        else:
            # 2) 캐시 미스: 실제 렌더링 수행
            video_path = render_premium_video(
                scenes=request.scenes,
                script_text=request.script_text or "",
                output_dir=str(videos_dir),
                render_mode=request.render_mode,
            )
            # 렌더링 성공 시 캐시 저장 시도
            try:
                save_final_cache(cache_key, Path(video_path))
            except Exception:
                pass
        
        # 상대 경로로 변환 (output 루트 기준)
        relative_path = Path(video_path).relative_to(output_root)
        video_url = f"/output/{relative_path.as_posix()}"
        
        return {
            "status": "ok",
            "success": True,
            "video_path": video_path,
            "video_url": video_url,
            "cached": cached_flag,
            "cache_key": cache_key,
            "message": "프리미엄 영상이 성공적으로 생성되었습니다."
        }
        
    except HTTPException:
        # HTTPException은 그대로 전달 (이미 적절한 status code 포함)
        raise
    except Exception as e:
        # 예상치 못한 오류
        raise HTTPException(
            status_code=500,
            detail=f"영상 생성 중 예상치 못한 오류 발생: {str(e)}"
        )


# ==== Job System: 비동기 프리미엄 렌더링 ====


def _append_job_log(job_id: str, message: str) -> str:
    """(호환용) 단순 메시지를 info 레벨 JSON 로그로 기록"""
    return _log_event(job_id=job_id, step="generic", message=message, level="INFO", extra=None)


def _log_event(
    job_id: str,
    step: str,
    message: str,
    level: str = "INFO",
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Job 로그 JSON Lines 포맷:
    ts, level, job_id, step, message, extra(optional)
    """
    log_path = logs_root / f"{job_id}.log"
    event: Dict[str, Any] = {
        "ts": datetime.now().isoformat(),
        "level": level,
        "job_id": job_id,
        "step": step,
        "message": message,
    }
    if extra:
        event["extra"] = extra

    try:
        line = json.dumps(event, ensure_ascii=False)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line)
    except Exception:
        # 로그 기록 실패는 렌더링 자체를 막지는 않음
        pass

    return str(log_path)


async def _run_premium_job(job_id: str, request_dict: Dict):
    """
    프리미엄 렌더링 Job 비동기 실행 함수
    - job_semaphore 로 동시 실행 개수 제한
    - Job 상태/로그 업데이트
    """
    async with job_semaphore:
        log_path = logs_root / f"{job_id}.log"
        try:
            update_job_status(
                job_id,
                status="running",
                message="렌더링을 시작합니다.",
                log_path=str(log_path),
            )
            _log_event(
                job_id=job_id,
                step="start",
                message=f"Job started (render_mode={request_dict.get('render_mode')})",
                level="INFO",
            )

            # 출력 디렉토리 설정
            backend_dir = Path(__file__).resolve().parent
            output_root = backend_dir / "output"
            videos_dir = output_root / "videos"

            # 실제 렌더 실행
            video_path = render_premium_video(
                scenes=request_dict["scenes"],
                script_text=request_dict.get("script_text") or "",
                output_dir=str(videos_dir),
                render_mode=request_dict.get("render_mode", "graphic"),
            )

            _log_event(
                job_id=job_id,
                step="final",
                message=f"Render finished: {video_path}",
                level="INFO",
            )

            update_job_status(
                job_id,
                status="done",
                message="렌더링이 완료되었습니다.",
                error_code=None,
                output_video_path=video_path,
                log_path=str(log_path),
            )
        except HTTPException as he:
            # HTTPException detail에서 error_code 추출 시도
            detail = he.detail
            error_code = None
            message = str(detail)
            if isinstance(detail, dict):
                error_code = detail.get("error_code")
                message = detail.get("message", message)

            _log_event(
                job_id=job_id,
                step="error_http",
                message=message,
                level="ERROR",
                extra={"error_code": error_code},
            )

            update_job_status(
                job_id,
                status="failed",
                message=message,
                error_code=error_code,
                log_path=str(log_path),
            )
        except Exception as e:
            tb = traceback.format_exc()
            _log_event(
                job_id=job_id,
                step="error_unexpected",
                message=str(e),
                level="ERROR",
                extra={"traceback": tb},
            )

            update_job_status(
                job_id,
                status="failed",
                message=str(e),
                error_code="unexpected_error",
                log_path=str(log_path),
            )


@app.post("/jobs/render/premium")
async def create_premium_render_job(request: PremiumRenderRequest):
    """
    프리미엄 렌더링 Job 생성 (비동기)
    - 기존 /video/render/premium 과 동일한 요청 바디 사용
    - 즉시 job_id를 반환하고, 실제 렌더링은 백그라운드에서 수행
    """
    # Job ID 및 입력 해시 생성
    job_id = uuid.uuid4().hex
    request_dict = request.model_dump()
    payload_json = json.dumps(request_dict, ensure_ascii=False, sort_keys=True)
    input_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    # 캐시 키 생성 (renderer_type + scenes + assets_version)
    cache_key = make_cache_key(request.render_mode, request.scenes)

    # renderer_version 추론
    renderer_version = "graphic_compositor_v1" if request.render_mode == "graphic" else "sd_renderer_v1"

    # 먼저 final 캐시 조회 (있으면 즉시 완료 처리)
    cached_final = has_final_cache(cache_key)
    if cached_final is not None:
        # final_<job_id>.mp4 생성
        backend_dir = Path(__file__).resolve().parent
        output_root = backend_dir / "output"
        final_video_path = output_root / f"final_{job_id}.mp4"
        final_video_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import shutil as _shutil
            _shutil.copy2(str(cached_final), str(final_video_path))
            # Job 레코드 생성 및 즉시 완료 처리
            create_job(
                job_id=job_id,
                job_type="render_premium",
                status="done",
                input_hash=input_hash,
                request_payload_json=payload_json,
                template_id=request.template_id,
                template_version=request.template_version,
                renderer_version=renderer_version,
                message="캐시된 결과를 사용하여 즉시 완료되었습니다.",
                log_path=str(logs_root / f"{job_id}.log"),
            )
            _append_job_log(job_id, f"[CACHE HIT] final cache_key={cache_key} path={cached_final}")
            update_job_status(
                job_id,
                status="done",
                output_video_path=str(final_video_path),
            )
            return {
                "status": "queued",
                "job_id": job_id,
                "cached": True,
                "cache_key": cache_key,
                "message": "프리미엄 렌더링 Job이 큐에 등록되었습니다. (캐시 히트)",
            }
        except Exception:
            # 캐시 사용 실패 시 일반 Job 큐 처리로 폴백
            pass

    # Job 레코드 생성 (캐시 미스 또는 캐시 사용 실패)
    create_job(
        job_id=job_id,
        job_type="render_premium",
        status="queued",
        input_hash=input_hash,
        request_payload_json=payload_json,
        template_id=request.template_id,
        template_version=request.template_version,
        renderer_version=renderer_version,
        message="프리미엄 렌더링 Job이 큐에 등록되었습니다.",
        log_path=str(logs_root / f"{job_id}.log"),
    )
    _log_event(
        job_id=job_id,
        step="cache",
        message="CACHE MISS",
        level="INFO",
        extra={"cache_key": cache_key},
    )

    # 비동기 Job 실행
    asyncio.create_task(_run_premium_job(job_id, request_dict))

    return {
        "status": "queued",
        "job_id": job_id,
        "cached": False,
        "cache_key": cache_key,
        "message": "프리미엄 렌더링 Job이 큐에 등록되었습니다.",
    }


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Job 상태 조회
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    return {
        "job_id": job["job_id"],
        "job_type": job["job_type"],
        "status": job["status"],
        "message": job["message"],
        "error_code": job["error_code"],
        "output_video_path": job["output_video_path"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "template_id": job["template_id"],
        "template_version": job["template_version"],
        "renderer_version": job["renderer_version"],
        "log_url": f"/jobs/{job_id}/logs_tail?tail=200",
        "log_download_url": f"/jobs/{job_id}/logs",
    }


@app.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    """
    Job 로그 텍스트 또는 tail JSON 반환
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    # DB에 log_path가 저장되어 있으면 우선 사용
    log_path_str = job.get("log_path") or str(logs_root / f"{job_id}.log")
    log_path = Path(log_path_str)

    if not log_path.exists() or not log_path.is_file():
        raise HTTPException(status_code=404, detail="log not found")

    # tail 파라미터가 없으면 기존처럼 파일 다운로드
    # (호환성 유지)
    # tail이 있으면 마지막 N줄을 JSON 배열로 반환
    tail: Optional[int] = None
    # FastAPI Query 사용이 어려우므로, request.query_params로 tail 처리하는 대신
    # 별도의 /jobs/{job_id}/logs_tail 엔드포인트를 사용하는 것이 더 안전하지만,
    # 요구사항에 맞춰 쿼리 파라미터 기반으로 처리 (간단 구현).
    # -> 별도 엔드포인트로 구현 아래 참고.

    return FileResponse(
        path=str(log_path),
        media_type="text/plain",
        filename=log_path.name,
    )


@app.get("/jobs/{job_id}/logs_tail")
async def get_job_logs_tail(job_id: str, tail: int = Query(200, description="마지막 N줄", example=200, ge=1, le=10000)):
    """
    Job 로그 마지막 N줄을 JSON 배열로 반환
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    log_path_str = job.get("log_path") or str(logs_root / f"{job_id}.log")
    log_path = Path(log_path_str)

    if not log_path.exists() or not log_path.is_file():
        raise HTTPException(status_code=404, detail="log not found")

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"log read error: {e}")

    tail_lines = lines[-tail:] if tail < len(lines) else lines
    events: List[Dict[str, Any]] = []
    for line in tail_lines:
        text = line.strip()
        if not text:
            continue
        try:
            events.append(json.loads(text))
        except Exception:
            events.append({"raw": text})

    return {
        "status": "ok",
        "job_id": job_id,
        "tail": tail,
        "count": len(events),
        "events": events,
    }


# 최신 final 영상 스트리밍 엔드포인트
@app.get("/video/latest")
async def get_latest_video():
    """
    backend/output 폴더에서 가장 최근 생성된 final_*.mp4를 스트리밍 반환
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        output_root = backend_dir / "output"
        output_root.mkdir(exist_ok=True)

        # final_*.mp4 파일 목록 수집
        final_files = list(output_root.glob("final_*.mp4"))
        if not final_files:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "no final video"}
            )

        # 최근 수정 시간 기준으로 정렬하여 최신 파일 선택
        latest_file = max(final_files, key=lambda p: p.stat().st_mtime)

        return FileResponse(
            path=str(latest_file),
            media_type="video/mp4",
            filename=latest_file.name
        )
    except Exception as e:
        # 예기치 못한 오류도 JSON 형태로 명확히 반환
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"latest video 조회 중 오류가 발생했습니다: {str(e)}"
            }
        )


# 특정 final 파일 스트리밍/다운로드 엔드포인트
@app.get("/video/file/{filename}")
async def get_video_file(filename: str):
    """
    특정 final_*.mp4 파일을 스트리밍/다운로드로 반환
    """
    # 보안 검증: 디렉토리 탈출 및 허용된 패턴만 통과
    if ".." in filename or "/" in filename or "\\" in filename:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "invalid filename"
            }
        )

    if not (filename.startswith("final_") and filename.endswith(".mp4")):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "only final_*.mp4 is allowed"
            }
        )

    backend_dir = Path(__file__).resolve().parent
    output_root = backend_dir / "output"
    file_path = output_root / filename

    if not file_path.exists() or not file_path.is_file():
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "message": "file not found"
            }
        )

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=file_path.name
    )


@app.get("/video/list")
async def list_videos(limit: int = Query(20, description="반환할 비디오 수", example=20, ge=1, le=100)):
    """
    backend/output 폴더에서 final_*.mp4 목록을 최신순으로 반환
    """
    backend_dir = Path(__file__).resolve().parent
    output_root = backend_dir / "output"
    output_root.mkdir(exist_ok=True)

    final_files = sorted(
        output_root.glob("final_*.mp4"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    items = []
    for p in final_files[: max(limit, 0)]:
        filename = p.name
        size = p.stat().st_size
        created_at = datetime.fromtimestamp(p.stat().st_mtime).isoformat()

        # job_id는 파일명에서 final_ 접두사 제거 후 .mp4 이전까지로 추출
        job_id = None
        if filename.startswith("final_") and filename.endswith(".mp4"):
            job_id = filename[len("final_") : -len(".mp4")]

        job_meta = get_job(job_id) if job_id else None

        items.append(
            {
                "filename": filename,
                "path": str(p),
                "size": size,
                "created_at": created_at,
                "job_id": job_id,
                "template_id": job_meta["template_id"] if job_meta else None,
                "template_version": job_meta["template_version"] if job_meta else None,
                "renderer_version": job_meta["renderer_version"] if job_meta else None,
            }
        )

    return {
        "status": "ok",
        "items": items,
    }


@app.get("/video/meta/{filename}")
async def get_video_meta(filename: str):
    """
    특정 final_*.mp4 파일의 메타데이터 반환
    """
    # 보안 검증
    if ".." in filename or "/" in filename or "\\" in filename:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "invalid filename",
            },
        )

    if not (filename.startswith("final_") and filename.endswith(".mp4")):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "only final_*.mp4 is allowed",
            },
        )

    backend_dir = Path(__file__).resolve().parent
    output_root = backend_dir / "output"
    file_path = output_root / filename

    if not file_path.exists() or not file_path.is_file():
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "message": "file not found",
            },
        )

    meta = probe_video_metadata(file_path)

    # job_id 및 job 메타 연결
    job_id = filename[len("final_") : -len(".mp4")]
    job_meta = get_job(job_id) if job_id else None

    return {
        "status": "ok",
        "filename": filename,
        "path": str(file_path),
        "job_id": job_id,
        "template_id": job_meta["template_id"] if job_meta else None,
        "template_version": job_meta["template_version"] if job_meta else None,
        "renderer_version": job_meta["renderer_version"] if job_meta else None,
        "duration": meta.get("duration"),
        "width": meta.get("width"),
        "height": meta.get("height"),
        "fps": meta.get("fps"),
        "size": meta.get("size"),
    }


# ==================== 롱폼 비디오 API ====================

class AnalyzeTemplateRequest(BaseModel):
    """템플릿 분석 요청"""
    example_script: str = Field(
        ..., 
        description="분석할 예시 스크립트",
        examples=[STEP2_TEXT]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "example_script": STEP2_TEXT
                }
            ]
        }
    )


@app.post("/longform/analyze-template")
async def analyze_template(request: AnalyzeTemplateRequest):
    """
    롱폼 템플릿 구성 분석
    
    예시 스크립트를 분석하여 롱폼 비디오의 구조적 패턴을 추출합니다.
    """
    try:
        analysis_result = analyze_template_structure(request.example_script)
        
        # 결과 저장
        backend_dir = Path(__file__).resolve().parent
        output_dir = backend_dir / "output" / "template_analysis"
        output_dir.mkdir(parents=True, exist_ok=True)
        latest_path = output_dir / "latest.json"
        save_analysis_result(analysis_result, latest_path)
        
        return {
            "status": "ok",
            "analysis": analysis_result,
            "saved_path": str(latest_path)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")


class CreatePlanRequest(BaseModel):
    """비디오 플랜 생성 요청"""
    topic: str = Field(..., description="비디오 주제", examples=[STEP2_TOPIC])
    template_analysis_id: str = Field("latest", description="템플릿 분석 ID (기본: latest)", examples=["latest"])
    style_profile_id: str = Field("longform-default", description="스타일 프로필 ID", examples=["longform-default"])
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "topic": STEP2_TOPIC,
                    "template_analysis_id": "latest",
                    "style_profile_id": "longform-default"
                }
            ]
        }
    )


@app.post("/longform/plan")
async def create_video_plan(request: CreatePlanRequest):
    """
    롱폼 비디오 플랜 생성
    
    주제와 템플릿 분석 결과를 기반으로 VideoPlanV1을 생성합니다.
    """
    try:
        # video_id 생성
        video_id = str(uuid.uuid4())
        
        # 템플릿 분석 결과 로드
        backend_dir = Path(__file__).resolve().parent
        analysis_dir = backend_dir / "output" / "template_analysis"
        analysis_result = None
        
        if request.template_analysis_id == "latest":
            analysis_result = load_latest_analysis(analysis_dir)
        else:
            analysis_path = analysis_dir / f"{request.template_analysis_id}.json"
            if analysis_path.exists():
                with open(analysis_path, "r", encoding="utf-8") as f:
                    analysis_result = json.load(f)
        
        # 스타일 프로필 로드
        style_profile = load_style_profile(request.style_profile_id)
        
        if not style_profile:
            raise HTTPException(
                status_code=404,
                detail=f"스타일 프로필을 찾을 수 없습니다: {request.style_profile_id}"
            )
        
        # VideoPlanV1 생성 (초기 상태, scenes는 비어있음)
        video_plan = VideoPlanV1(
            video_id=video_id,
            topic=request.topic,
            style_profile_id=request.style_profile_id,
            narration_script="",  # 나중에 split에서 채워짐
            scenes=[],
            chapters=[],
            meta={
                "template_analysis_id": request.template_analysis_id,
                "template_analysis": analysis_result,
                "style_profile": style_profile,
                "created_at": datetime.now().isoformat()
            }
        )
        
        # 플랜 저장
        plans_dir = backend_dir / "output" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        plan_path = plans_dir / f"{video_id}.json"
        save_video_plan(video_plan, plan_path)
        
        return {
            "status": "ok",
            "video_plan": video_plan.model_dump(),
            "saved_path": str(plan_path)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"플랜 생성 중 오류 발생: {str(e)}")


@app.get("/longform/plan/{video_id}")
async def get_video_plan(video_id: str):
    """
    비디오 플랜 조회
    
    video_id로 저장된 VideoPlanV1을 조회합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        plan_path = backend_dir / "output" / "plans" / f"{video_id}.json"
        
        video_plan = load_video_plan(plan_path)
        
        if not video_plan:
            raise HTTPException(
                status_code=404,
                detail=f"비디오 플랜을 찾을 수 없습니다: {video_id}"
            )
        
        return {
            "status": "ok",
            "video_plan": video_plan.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"플랜 조회 중 오류 발생: {str(e)}")


class SplitScriptRequest(BaseModel):
    """스크립트 분해 요청"""
    full_script: Optional[str] = Field(
        None, 
        description="전체 스크립트 (없으면 topic 기반 생성)",
        examples=[STEP2_TEXT]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "full_script": STEP2_TEXT
                }
            ]
        }
    )


@app.post("/longform/plan/{video_id}/split")
async def split_script_to_scenes_endpoint(video_id: str, request: SplitScriptRequest):
    """
    롱폼 스크립트 → 씬 자동 분해
    
    전체 스크립트를 씬 단위로 분해하여 VideoPlanV1을 업데이트합니다.
    full_script가 없으면 topic 기반 임시 롱폼 스크립트를 생성 후 분해합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        plan_path = backend_dir / "output" / "plans" / f"{video_id}.json"
        
        # 기존 플랜 로드
        video_plan = load_video_plan(plan_path)
        
        if not video_plan:
            raise HTTPException(
                status_code=404,
                detail=f"비디오 플랜을 찾을 수 없습니다: {video_id}"
            )
        
        # full_script가 없으면 topic 기반 임시 스크립트 생성
        full_script = request.full_script
        if not full_script or not full_script.strip():
            # 간단한 임시 스크립트 생성 (실제로는 더 정교한 생성 로직 필요)
            full_script = _generate_temp_longform_script(video_plan.topic)
        
        # 템플릿 분석 결과 로드 (hook_rules 등)
        analysis_dir = backend_dir / "output" / "template_analysis"
        analysis_result = load_latest_analysis(analysis_dir)
        hook_rules = analysis_result.get("hook_rules", []) if analysis_result else None
        
        # 스타일 프로필 로드
        style_profile = load_style_profile(video_plan.style_profile_id)
        
        # 스크립트 분해
        updated_plan = split_script_to_scenes(
            full_script,
            video_plan,
            hook_rules=hook_rules,
            style_profile=style_profile
        )
        
        # 플랜 저장
        save_video_plan(updated_plan, plan_path)
        
        # verify 텍스트 파일 저장 (스크립트/씬 확정 시점)
        verify_outputs = {}
        try:
            # 새로운 export 형식: output/verify/<run_id>/
            plan_dict = updated_plan.model_dump()
            export_files = export_verify_from_plan(
                plan_dict,
                video_id,
                backend_dir / "output"
            )
            
            # 기존 형식도 유지 (하위 호환성)
            legacy_files = save_verify_outputs_from_plan(
                updated_plan,
                video_id,
                backend_dir / "output"
            )
            
            verify_outputs = {
                "script_url": f"/verify/texts/script_{video_id}.txt",
                "scenes_url": f"/verify/texts/scenes_{video_id}.txt",
                "export_dir": f"/verify/{video_id}/",
                "export_files": export_files
            }
            print(f"[VERIFY_EXPORT] verify 파일 생성 완료: video_id={video_id}")
        except Exception as e:
            error_msg = f"verify 파일 저장 실패: {e}"
            print(f"[VERIFY_EXPORT] WARN: {error_msg}")
        
        return {
            "status": "ok",
            "video_plan": updated_plan.model_dump(),
            "scene_count": len(updated_plan.scenes),
            "verify_outputs": verify_outputs
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스크립트 분해 중 오류 발생: {str(e)}")


def _generate_temp_longform_script(topic: str) -> str:
    """
    topic 기반 임시 롱폼 스크립트 생성
    
    Args:
        topic: 비디오 주제
    
    Returns:
        str: 생성된 임시 스크립트
    """
    # 간단한 템플릿 기반 생성 (실제로는 AI 기반 생성 필요)
    script = f"""안녕하세요. 오늘은 {topic}에 대해 이야기해보겠습니다.

많은 분들이 {topic}에 대해 궁금해하시는데요. 실제로 이 주제는 우리 일상과 밀접한 관련이 있습니다.

먼저 {topic}의 기본 개념부터 살펴보겠습니다. 이는 매우 중요한 요소입니다.

다음으로 {topic}의 실제 사례를 통해 더 깊이 이해해보겠습니다. 여러분도 한 번쯤 경험해보셨을 것입니다.

마지막으로 {topic}에 대한 핵심 요약과 앞으로의 전망을 정리해보겠습니다.

이상으로 {topic}에 대한 이야기를 마치겠습니다. 감사합니다."""
    
    return script


# ==================== 롱폼 렌더링 API ====================

# 렌더링 중인 video_id 추적 (중복 실행 방지)
_rendering_videos: set[str] = set()


class RenderRequest(BaseModel):
    """롱폼 렌더 요청"""
    render_mode: Literal["graphic", "sd"] = Field("graphic", description="렌더 모드", examples=["graphic"])
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "render_mode": "graphic"
                }
            ]
        }
    )


@app.post("/longform/render/{video_id}")
async def render_longform_video_endpoint(video_id: str, request: RenderRequest):
    """
    롱폼 비디오 렌더링 실행
    
    씬 단위로 순차 렌더링하며, 중간 실패 시 재개 가능합니다.
    이미 렌더 중인 경우 중복 실행을 방지합니다.
    """
    # 중복 실행 방지
    if video_id in _rendering_videos:
        raise HTTPException(
            status_code=409,
            detail=f"비디오 {video_id}는 이미 렌더링 중입니다."
        )
    
    try:
        _rendering_videos.add(video_id)
        
        backend_dir = Path(__file__).resolve().parent
        result = render_longform_video(
            video_id=video_id,
            plan_path=None,  # 자동 탐색
            render_mode=request.render_mode,
            backend_dir=backend_dir
        )
        
        return {
            "status": "ok",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"렌더링 중 오류 발생: {str(e)}"
        )
    finally:
        # 렌더링 완료 후 추적에서 제거
        _rendering_videos.discard(video_id)


# ==================== 롱폼 씬 검토/프리뷰 API ====================

@app.get("/longform/review/{video_id}")
async def get_review_data(video_id: str):
    """
    롱폼 씬 검토용 조회 API
    
    렌더 실행 이전/중간/이후 모두에서 씬 상태를 확인할 수 있습니다.
    
    v1.4 Step6/10 검증 404 해결:
    - plans 파일이 없으면 run 폴더에서 자동 복구/저장
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        plan_path = backend_dir / "output" / "plans" / f"{video_id}.json"
        
        # 플랜 파일이 없으면 폴백 시도
        if not plan_path.exists():
            # run_dir 확인 (video_id가 run_id인 경우)
            from backend.utils.run_manager import get_run_dir
            run_dir = get_run_dir(video_id, base_dir=backend_dir)
            scenes_fixed_path = run_dir / "step3" / "scenes_fixed.json"
            
            if scenes_fixed_path.exists():
                # scenes_fixed.json을 기반으로 VideoPlanV1 생성
                try:
                    # script.txt 로드 (없으면 빈 문자열)
                    script_path = run_dir / "step2" / "script.txt"
                    narration_script = ""
                    if script_path.exists():
                        narration_script = script_path.read_text(encoding="utf-8", errors="ignore").strip()
                    
                    # scenes_fixed.json 로드
                    with open(scenes_fixed_path, "r", encoding="utf-8") as f:
                        scenes_fixed_data = json.load(f)
                    
                    scenes_list = scenes_fixed_data.get("scenes", [])
                    if scenes_list:
                        # VideoPlanV1 생성
                        from backend.schemas.longform_scene_v1 import SceneV1
                        
                        # topic 추출
                        topic = "Untitled"
                        if narration_script:
                            lines = narration_script.splitlines()
                            for line in lines:
                                line = line.strip()
                                if line:
                                    topic = line[:60]
                                    break
                        
                        # scenes 배열 생성
                        scenes = []
                        for i, scene_fixed in enumerate(scenes_list):
                            scene_index = scene_fixed.get("scene_index", i)
                            order = scene_index + 1 if scene_index > 0 else i + 1
                            scene_id = f"scene_{order:03d}"
                            narration = scene_fixed.get("narration", "")
                            shot_prompt_en = scene_fixed.get("visual_prompt", "")
                            duration_sec = scene_fixed.get("duration_sec", 6)
                            duration_sec = max(1, min(60, int(duration_sec)))
                            
                            scene = SceneV1(
                                scene_id=scene_id,
                                order=order,
                                narration=narration,
                                shot_prompt_en=shot_prompt_en,
                                image_asset=None,
                                duration_sec=duration_sec,
                                overlay_text=None,
                                bgm=None,
                                status="pending",
                                render_status="PENDING",
                                render_attempts=0,
                                last_error=None,
                                output_video_path=None
                            )
                            scenes.append(scene)
                        
                        # VideoPlanV1 생성 및 저장
                        video_plan = VideoPlanV1(
                            video_id=video_id,
                            topic=topic,
                            style_profile_id="longform-default",
                            narration_script=narration_script,
                            scenes=scenes,
                            chapters=[],
                            meta={
                                "source": "auto_backfill_from_review_api",
                                "from": f"runs/{video_id}/step3/scenes_fixed.json"
                            }
                        )
                        
                        # 저장
                        plan_path.parent.mkdir(parents=True, exist_ok=True)
                        save_video_plan(video_plan, plan_path)
                except Exception as e:
                    # 폴백 실패 시 기존 404 유지
                    raise HTTPException(
                        status_code=404,
                        detail=f"비디오 플랜을 찾을 수 없습니다: {video_id} (폴백 실패: {str(e)})"
                    )
            else:
                # 폴백 소스도 없으면 404
                raise HTTPException(
                    status_code=404,
                    detail=f"비디오 플랜을 찾을 수 없습니다: {video_id}"
                )
        
        # 플랜 로드
        video_plan = load_video_plan(plan_path)
        
        if not video_plan:
            raise HTTPException(
                status_code=500,
                detail="플랜 로드 실패"
            )
        
        # 씬을 order 기준으로 정렬
        sorted_scenes = sorted(video_plan.scenes, key=lambda s: s.order)
        
        # 씬 정보 추출
        scenes_data = []
        for scene in sorted_scenes:
            # image_asset 처리: 절대경로/URL 그대로 반환, 없으면 null
            image_asset_url = None
            if scene.image_asset:
                # 절대경로인 경우 그대로 사용
                if scene.image_asset.startswith("http://") or scene.image_asset.startswith("https://"):
                    image_asset_url = scene.image_asset
                elif Path(scene.image_asset).is_absolute():
                    image_asset_url = scene.image_asset
                else:
                    # 상대경로인 경우 assets 디렉토리 기준으로 변환
                    assets_path = backend_dir / "assets" / scene.image_asset
                    if assets_path.exists():
                        # 정적 파일 서빙 경로로 변환
                        image_asset_url = f"/static/assets/{scene.image_asset}"
                    else:
                        image_asset_url = scene.image_asset  # 원본 그대로
            
            # v1.4 Step10: Lock 상태 확인
            locked = False
            try:
                manifest = load_run_manifest(video_id, base_dir=backend_dir)
                if manifest and manifest.get("locks", {}).get("scenes", {}).get(scene.scene_id, {}).get("locked", False):
                    locked = True
            except Exception:
                pass
            
            scene_info = {
                "scene_id": scene.scene_id,
                "order": scene.order,
                "narration": scene.narration,
                "shot_prompt_en": scene.shot_prompt_en,
                "image_asset": image_asset_url,
                "duration_sec": scene.duration_sec,
                "render_status": scene.render_status,
                "render_attempts": scene.render_attempts,
                "last_error": scene.last_error,
                "locked": locked  # v1.4 Step10: Lock 상태 포함
            }
            scenes_data.append(scene_info)
        
        # 상태 요약 계산
        status_summary = {
            "total": len(scenes_data),
            "pending": sum(1 for s in scenes_data if s["render_status"] == "PENDING"),
            "running": sum(1 for s in scenes_data if s["render_status"] == "RUNNING"),
            "done": sum(1 for s in scenes_data if s["render_status"] == "DONE"),
            "failed": sum(1 for s in scenes_data if s["render_status"] == "FAILED"),
            "skipped": sum(1 for s in scenes_data if s["render_status"] == "SKIPPED")
        }
        
        return {
            "status": "ok",
            "video_id": video_id,
            "topic": video_plan.topic,
            "style_profile_id": video_plan.style_profile_id,
            "scenes": scenes_data,
            "summary": status_summary
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"검토 데이터 조회 중 오류 발생: {str(e)}"
        )


class SceneUpdateRequest(BaseModel):
    """씬 수정 요청"""
    narration: Optional[str] = Field(None, description="내레이션 텍스트 (한국어)", examples=[SAMPLE_SENTENCE])
    shot_prompt_en: Optional[str] = Field(None, description="이미지 생성 프롬프트 (영어)", examples=["cinematic, professional, calm, informative"])
    duration_sec: Optional[int] = Field(None, description="씬 지속 시간 (초)", ge=1, le=60, examples=[8])
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "narration": SAMPLE_SENTENCE,
                    "shot_prompt_en": "cinematic, professional, calm, informative",
                    "duration_sec": 8
                }
            ]
        }
    )


@app.patch("/longform/review/{video_id}/scene/{scene_id}")
async def update_scene(
    video_id: str,
    scene_id: str,
    request: SceneUpdateRequest
):
    """
    씬 단위 수정 API
    
    렌더 전용 수정: narration, shot_prompt_en, duration_sec만 수정 가능.
    render_status == DONE 인 씬은 수정 불가.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        plan_path = backend_dir / "output" / "plans" / f"{video_id}.json"
        
        if not plan_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"비디오 플랜을 찾을 수 없습니다: {video_id}"
            )
        
        # 플랜 로드
        video_plan = load_video_plan(plan_path)
        
        if not video_plan:
            raise HTTPException(
                status_code=500,
                detail="플랜 로드 실패"
            )
        
        # 씬 찾기
        scene = None
        for s in video_plan.scenes:
            if s.scene_id == scene_id:
                scene = s
                break
        
        if not scene:
            raise HTTPException(
                status_code=404,
                detail=f"씬을 찾을 수 없습니다: {scene_id}"
            )
        
        # DONE 상태 씬은 수정 불가
        if scene.render_status == "DONE":
            raise HTTPException(
                status_code=400,
                detail=f"이미 렌더링이 완료된 씬({scene_id})은 수정할 수 없습니다."
            )
        
        # 수정 가능한 필드만 업데이트
        if request.narration is not None:
            scene.narration = request.narration
        
        if request.shot_prompt_en is not None:
            scene.shot_prompt_en = request.shot_prompt_en
        
        if request.duration_sec is not None:
            scene.duration_sec = request.duration_sec
        
        # 수정 시 렌더 상태 초기화
        scene.render_status = "PENDING"
        scene.output_video_path = None
        scene.render_attempts = 0
        scene.last_error = None
        
        # 플랜 즉시 저장
        save_video_plan(video_plan, plan_path)
        
        return {
            "status": "ok",
            "message": f"씬 {scene_id} 수정 완료",
            "scene": {
                "scene_id": scene.scene_id,
                "order": scene.order,
                "narration": scene.narration,
                "shot_prompt_en": scene.shot_prompt_en,
                "duration_sec": scene.duration_sec,
                "render_status": scene.render_status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"씬 수정 중 오류 발생: {str(e)}"
        )


# ==================== v1.4 Step10: Scene Lock 기능 ====================

class SceneLockRequest(BaseModel):
    """씬 Lock 요청"""
    reason: Optional[str] = Field(None, description="Lock 이유")


class SceneUnlockRequest(BaseModel):
    """씬 Unlock 요청"""
    reason: Optional[str] = Field(None, description="Unlock 이유")


@app.post("/longform/lock/{video_id}/scene/{scene_id}")
async def lock_scene(
    video_id: str,
    scene_id: str,
    request: SceneLockRequest = Body(...)
):
    """
    씬 Lock (v1.4 Step10)
    
    해당 scene을 고정하여 regenerate/render 시 재사용합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        
        # manifest 로드
        manifest = load_run_manifest(video_id, base_dir=backend_dir)
        if manifest is None:
            raise HTTPException(
                status_code=404,
                detail=f"Manifest를 찾을 수 없습니다: {video_id}"
            )
        
        # locks 백필
        if "locks" not in manifest:
            manifest["locks"] = {"scenes": {}}
        if "scenes" not in manifest["locks"]:
            manifest["locks"]["scenes"] = {}
        
        # scene이 plan에 존재하는지 확인
        plan_path = backend_dir / "output" / "plans" / f"{video_id}.json"
        if not plan_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"비디오 플랜을 찾을 수 없습니다: {video_id}"
            )
        
        video_plan = load_video_plan(plan_path)
        if not video_plan:
            raise HTTPException(status_code=500, detail="플랜 로드 실패")
        
        scene_exists = any(s.scene_id == scene_id for s in video_plan.scenes)
        if not scene_exists:
            raise HTTPException(
                status_code=404,
                detail=f"씬을 찾을 수 없습니다: {scene_id}"
            )
        
        # lock 설정
        manifest["locks"]["scenes"][scene_id] = {
            "locked": True,
            "locked_at": datetime.now().isoformat(),
            "reason": request.reason
        }
        
        # manifest 저장
        from backend.utils.run_manager import update_run_manifest
        update_run_manifest(video_id, {"locks": manifest["locks"]}, base_dir=backend_dir)
        
        # decision_trace 기록
        try:
            append_decision_trace(
                video_id,
                {
                    "action": "scene_lock",
                    "scene_id": scene_id,
                    "reason": request.reason
                },
                base_dir=backend_dir
            )
        except Exception:
            pass
        
        # 이벤트 로그 기록
        try:
            write_event(
                video_id,
                "scene_locked",
                {
                    "video_id": video_id,
                    "scene_id": scene_id,
                    "reason": request.reason
                },
                base_dir=backend_dir
            )
        except Exception:
            pass
        
        # 메트릭 업데이트
        try:
            metrics = ensure_metrics(video_id, base_dir=backend_dir)
            metrics["scene_lock_count"] = metrics.get("scene_lock_count", 0) + 1
            update_metrics(video_id, metrics, base_dir=backend_dir)
        except Exception:
            pass
        
        return {
            "status": "ok",
            "message": f"씬 {scene_id} Lock 완료",
            "scene_id": scene_id,
            "locked": True,
            "locked_at": manifest["locks"]["scenes"][scene_id]["locked_at"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"씬 Lock 중 오류 발생: {str(e)}"
        )


@app.post("/longform/unlock/{video_id}/scene/{scene_id}")
async def unlock_scene(
    video_id: str,
    scene_id: str,
    request: SceneUnlockRequest = Body(...)
):
    """
    씬 Unlock (v1.4 Step10)
    
    해당 scene의 Lock을 해제합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        
        # manifest 로드
        manifest = load_run_manifest(video_id, base_dir=backend_dir)
        if manifest is None:
            raise HTTPException(
                status_code=404,
                detail=f"Manifest를 찾을 수 없습니다: {video_id}"
            )
        
        # locks 백필
        if "locks" not in manifest:
            manifest["locks"] = {"scenes": {}}
        if "scenes" not in manifest["locks"]:
            manifest["locks"]["scenes"] = {}
        
        # unlock 설정
        if scene_id in manifest["locks"]["scenes"]:
            manifest["locks"]["scenes"][scene_id]["locked"] = False
            manifest["locks"]["scenes"][scene_id]["unlocked_at"] = datetime.now().isoformat()
            if request.reason:
                manifest["locks"]["scenes"][scene_id]["unlock_reason"] = request.reason
        else:
            # 이미 unlock 상태
            manifest["locks"]["scenes"][scene_id] = {
                "locked": False,
                "unlocked_at": datetime.now().isoformat(),
                "reason": request.reason
            }
        
        # manifest 저장
        from backend.utils.run_manager import update_run_manifest
        update_run_manifest(video_id, {"locks": manifest["locks"]}, base_dir=backend_dir)
        
        # decision_trace 기록
        try:
            append_decision_trace(
                video_id,
                {
                    "action": "scene_unlock",
                    "scene_id": scene_id,
                    "reason": request.reason
                },
                base_dir=backend_dir
            )
        except Exception:
            pass
        
        # 이벤트 로그 기록
        try:
            write_event(
                video_id,
                "scene_unlocked",
                {
                    "video_id": video_id,
                    "scene_id": scene_id,
                    "reason": request.reason
                },
                base_dir=backend_dir
            )
        except Exception:
            pass
        
        return {
            "status": "ok",
            "message": f"씬 {scene_id} Unlock 완료",
            "scene_id": scene_id,
            "locked": False,
            "unlocked_at": manifest["locks"]["scenes"][scene_id].get("unlocked_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"씬 Unlock 중 오류 발생: {str(e)}"
        )


# ==================== v1.4 Step6: Scene 단위 Retry/Resume ====================

class SceneRegenerateRequest(BaseModel):
    """씬 텍스트 재생성 요청"""
    reason: Optional[str] = Field(None, description="재생성 이유")
    seed_override: Optional[int] = Field(None, description="시드 오버라이드 (재현성용)")


class SceneRenderRequest(BaseModel):
    """씬 렌더 재시도 요청"""
    force: bool = Field(False, description="강제 재렌더링 (이미 DONE이어도)")
    reason: Optional[str] = Field(None, description="재렌더 이유")


@app.post("/longform/retry/{video_id}/scene/{scene_id}/regenerate")
async def regenerate_scene_text(
    video_id: str,
    scene_id: str,
    request: SceneRegenerateRequest = Body(...)
):
    """
    씬 텍스트(나레이션/프롬프트) 재생성 (v1.4 Step6)
    
    해당 scene의 텍스트만 재생성하여 plan/review JSON에 반영합니다.
    render_status가 DONE이어도 텍스트 재생성은 가능하되, 렌더는 자동 수행하지 않습니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        plan_path = backend_dir / "output" / "plans" / f"{video_id}.json"
        
        if not plan_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"비디오 플랜을 찾을 수 없습니다: {video_id}"
            )
        
        # 플랜 로드
        video_plan = load_video_plan(plan_path)
        if not video_plan:
            raise HTTPException(status_code=500, detail="플랜 로드 실패")
        
        # 씬 찾기
        target_scene = None
        scene_index = -1
        for idx, scene in enumerate(video_plan.scenes):
            if scene.scene_id == scene_id:
                target_scene = scene
                scene_index = idx
                break
        
        if not target_scene:
            raise HTTPException(
                status_code=404,
                detail=f"씬을 찾을 수 없습니다: {scene_id}"
            )
        
        # v1.4 Step10: Lock 체크
        manifest = load_run_manifest(video_id, base_dir=backend_dir)
        if manifest and manifest.get("locks", {}).get("scenes", {}).get(scene_id, {}).get("locked", False):
            raise HTTPException(
                status_code=409,
                detail=f"씬 {scene_id}이(가) Lock되어 있어 재생성할 수 없습니다."
            )
        
        # 변경 전 해시 (before_hash)
        before_hash = hashlib.md5(
            (target_scene.narration + target_scene.shot_prompt_en).encode()
        ).hexdigest()[:16]
        
        # 텍스트 재생성: split_script_to_scenes 로직 재사용하여 해당 scene만 재생성
        try:
            # 스타일 프로필 로드
            style_profile = load_style_profile(video_plan.style_profile_id)
            
            # split_script_to_scenes의 내부 함수를 재사용하여 shot_prompt_en 재생성
            narration = target_scene.narration
            if not narration or not narration.strip():
                # narration이 없으면 topic 기반 생성
                narration = f"{video_plan.topic}에 대한 설명"
            
            # shot_prompt_en 재생성 (split_script_to_scenes 로직 재사용)
            shot_prefix = ""
            shot_suffix = ""
            if style_profile:
                shot_prefix = style_profile.get("shot_prompt_prefix", "")
                shot_suffix = style_profile.get("shot_prompt_suffix", "")
            
            # _generate_shot_prompt 재사용 (없으면 fallback)
            if _generate_shot_prompt:
                shot_prompt_en = _generate_shot_prompt(narration, shot_prefix, shot_suffix)
            else:
                # fallback: 간단한 키워드 기반 생성
                shot_prompt_en = f"cinematic, professional, informative, calm"
            
            # scene 업데이트
            target_scene.shot_prompt_en = shot_prompt_en
            # narration은 유지 (필요시 업데이트 가능)
            
            # render_status가 DONE이 아니면 PENDING으로 변경 (렌더 재요청)
            if target_scene.render_status == "DONE":
                # DONE이면 텍스트만 업데이트하고 렌더는 자동 수행 안 함
                pass
            else:
                # DONE이 아니면 PENDING으로 초기화
                target_scene.render_status = "PENDING"
                target_scene.render_attempts = 0
                target_scene.last_error = None
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"씬 텍스트 재생성 중 오류 발생: {str(e)}"
            )
        
        # 변경 후 해시 (after_hash)
        after_hash = hashlib.md5(
            (target_scene.narration + target_scene.shot_prompt_en).encode()
        ).hexdigest()[:16]
        
        # 플랜 저장
        save_video_plan(video_plan, plan_path)
        
        # decision_trace 기록 (video_id를 run_id로 사용)
        try:
            append_decision_trace(
                video_id,
                {
                    "action": "scene_regenerate",
                    "scene_id": scene_id,
                    "reason": request.reason,
                    "before_hash": before_hash,
                    "after_hash": after_hash,
                    "seed_override": request.seed_override
                },
                base_dir=backend_dir
            )
        except Exception:
            pass  # decision_trace 실패는 무시
        
        # 이벤트 로그 기록
        try:
            write_event(
                video_id,
                "scene_retry_regenerate",
                {
                    "video_id": video_id,
                    "scene_id": scene_id,
                    "reason": request.reason,
                    "before_hash": before_hash,
                    "after_hash": after_hash
                },
                base_dir=backend_dir
            )
        except Exception:
            pass  # 이벤트 로그 실패는 무시
        
        # 메트릭 업데이트
        try:
            metrics = ensure_metrics(video_id, base_dir=backend_dir)
            metrics["scene_retry_regenerate_count"] = metrics.get("scene_retry_regenerate_count", 0) + 1
            update_metrics(video_id, metrics, base_dir=backend_dir)
        except Exception:
            pass  # 메트릭 업데이트 실패는 무시
        
        return {
            "status": "ok",
            "message": f"씬 {scene_id} 텍스트 재생성 완료",
            "scene": {
                "scene_id": target_scene.scene_id,
                "order": target_scene.order,
                "narration": target_scene.narration,
                "shot_prompt_en": target_scene.shot_prompt_en,
                "render_status": target_scene.render_status
            },
            "before_hash": before_hash,
            "after_hash": after_hash
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"씬 텍스트 재생성 중 오류 발생: {str(e)}"
        )


@app.post("/longform/retry/{video_id}/scene/{scene_id}/render")
async def retry_scene_render(
    video_id: str,
    scene_id: str,
    request: SceneRenderRequest = Body(...)
):
    """
    씬 렌더 재시도 (v1.4 Step6)
    
    해당 scene만 렌더 재실행하여 이미지/비디오 산출물을 갱신합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        plan_path = backend_dir / "output" / "plans" / f"{video_id}.json"
        
        if not plan_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"비디오 플랜을 찾을 수 없습니다: {video_id}"
            )
        
        # 플랜 로드
        video_plan = load_video_plan(plan_path)
        if not video_plan:
            raise HTTPException(status_code=500, detail="플랜 로드 실패")
        
        # 씬 찾기
        target_scene = None
        for scene in video_plan.scenes:
            if scene.scene_id == scene_id:
                target_scene = scene
                break
        
        if not target_scene:
            raise HTTPException(
                status_code=404,
                detail=f"씬을 찾을 수 없습니다: {scene_id}"
            )
        
        # v1.4 Step10: Lock 체크
        manifest = load_run_manifest(video_id, base_dir=backend_dir)
        is_locked = manifest and manifest.get("locks", {}).get("scenes", {}).get(scene_id, {}).get("locked", False)
        if is_locked and not request.force:
            raise HTTPException(
                status_code=409,
                detail=f"씬 {scene_id}이(가) Lock되어 있어 렌더할 수 없습니다. force=true 옵션을 사용하세요."
            )
        
        # force가 아니고 DONE이면 에러
        if not request.force and target_scene.render_status == "DONE":
            raise HTTPException(
                status_code=400,
                detail=f"씬 {scene_id}은 이미 렌더링이 완료되었습니다. --force 옵션을 사용하세요."
            )
        
        # render_status를 RETRY_REQUESTED로 설정
        old_status = target_scene.render_status
        target_scene.render_status = "RETRY_REQUESTED"
        target_scene.render_attempts = 0
        target_scene.last_error = None
        target_scene.output_video_path = None
        
        # 플랜 저장
        save_video_plan(video_plan, plan_path)
        
        # 렌더 실행 (기존 render_longform_video 함수 재사용)
        # 주의: render_longform_video는 전체 씬을 렌더하지만, 여기서는 해당 scene만 렌더
        # 실제로는 render_longform_video 내부 로직을 scene 단위로 호출해야 함
        # 여기서는 간단하게 render_status를 RUNNING으로 변경하고, 실제 렌더는 백그라운드 작업으로 처리
        target_scene.render_status = "RUNNING"
        save_video_plan(video_plan, plan_path)
        
        # decision_trace 기록
        try:
            append_decision_trace(
                video_id,
                {
                    "action": "scene_render_retry",
                    "scene_id": scene_id,
                    "reason": request.reason,
                    "force": request.force,
                    "old_status": old_status
                },
                base_dir=backend_dir
            )
        except Exception:
            pass
        
        # 이벤트 로그 기록
        try:
            write_event(
                video_id,
                "scene_retry_render",
                {
                    "video_id": video_id,
                    "scene_id": scene_id,
                    "reason": request.reason,
                    "force": request.force,
                    "old_status": old_status
                },
                base_dir=backend_dir
            )
        except Exception:
            pass
        
        # 메트릭 업데이트
        try:
            metrics = ensure_metrics(video_id, base_dir=backend_dir)
            metrics["scene_retry_render_count"] = metrics.get("scene_retry_render_count", 0) + 1
            update_metrics(video_id, metrics, base_dir=backend_dir)
        except Exception:
            pass
        
        # 실제 렌더 실행은 별도 백그라운드 작업으로 처리
        # 여기서는 상태 변경만 수행
        return {
            "status": "ok",
            "message": f"씬 {scene_id} 렌더 재시도 요청됨",
            "scene": {
                "scene_id": target_scene.scene_id,
                "order": target_scene.order,
                "render_status": target_scene.render_status,
                "render_attempts": target_scene.render_attempts
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"씬 렌더 재시도 중 오류 발생: {str(e)}"
        )


@app.get("/review/{video_id}", response_class=HTMLResponse)
async def review_page(video_id: str):
    """
    롱폼 씬 검토 페이지 (프론트엔드)
    
    /review/{video_id} 경로로 접근하면 review.html을 반환합니다.
    """
    review_html_path = static_dir / "review.html"
    
    if not review_html_path.exists():
        raise HTTPException(
            status_code=404,
            detail="검토 페이지를 찾을 수 없습니다."
        )
    
    with open(review_html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content)


# ==================== 유튜브 메타데이터 생성 API ====================

from backend.ai_engine.youtube_metadata_generator import generate_youtube_metadata


@app.post("/longform/youtube/{video_id}")
async def generate_youtube_metadata_endpoint(video_id: str):
    """
    롱폼 영상 기반 유튜브 업로드 메타데이터 자동 생성
    
    렌더 실패/미완성 상태에서도 실행 가능합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        plan_path = backend_dir / "output" / "plans" / f"{video_id}.json"
        
        if not plan_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"비디오 플랜을 찾을 수 없습니다: {video_id}"
            )
        
        # 플랜 로드
        video_plan = load_video_plan(plan_path)
        
        if not video_plan:
            raise HTTPException(
                status_code=500,
                detail="플랜 로드 실패"
            )
        
        # 씬 검증: 빈 narration 씬 제외
        valid_scenes = [s for s in video_plan.scenes if s.narration and s.narration.strip()]
        
        if not valid_scenes:
            raise HTTPException(
                status_code=400,
                detail="유효한 씬이 없습니다. narration이 있는 씬이 필요합니다."
            )
        
        # 유튜브 메타데이터 생성
        metadata = generate_youtube_metadata(video_plan)
        
        # 검증: scenes 합계 duration_sec == 챕터 마지막 타임라인 일치
        total_duration = sum(s.duration_sec for s in valid_scenes)
        if metadata["chapters"]:
            last_chapter_sec = metadata["chapters"][-1]["start_sec"]
            # 마지막 씬의 duration 추가
            sorted_scenes = sorted(valid_scenes, key=lambda s: s.order)
            last_scene_duration = sorted_scenes[-1].duration_sec
            calculated_end = last_chapter_sec + last_scene_duration
            
            # 오차 허용 범위 (5초)
            if abs(total_duration - calculated_end) > 5:
                # 경고만 (에러는 아님)
                print(f"[WARN] duration 불일치: total={total_duration}, calculated={calculated_end}")
        
        # 결과 저장
        youtube_output_dir = backend_dir / "output" / "youtube"
        youtube_output_dir.mkdir(parents=True, exist_ok=True)
        output_path = youtube_output_dir / f"{video_id}.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "ok",
            **metadata,
            "saved_path": str(output_path)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"유튜브 메타데이터 생성 중 오류 발생: {str(e)}"
        )


# ==================== 체크프롬프트 시스템 (v2) ====================

from backend.checkprompts.runner import run_longform_script_pipeline


@app.get("/dev/checkprompts")
async def get_checkprompts():
    """
    체크프롬프트 목록 조회
    
    registry.json의 prompt 목록을 반환합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        registry_path = backend_dir / "checkprompts" / "registry.json"
        
        if not registry_path.exists():
            raise HTTPException(
                status_code=404,
                detail="체크프롬프트 레지스트리를 찾을 수 없습니다."
            )
        
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        
        return {
            "status": "ok",
            "version": registry.get("version"),
            "description": registry.get("description"),
            "prompts": list(registry.get("prompts", {}).keys())
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"체크프롬프트 목록 조회 중 오류 발생: {str(e)}"
        )


class RunCheckPromptsRequest(BaseModel):
    """체크프롬프트 실행 요청"""
    names: List[str] = Field(..., description="실행할 체크프롬프트 이름 리스트", examples=[["step1_basic", "step1_cache_hit"]])
    repeat: int = Field(1, description="반복 횟수", ge=1, le=10, examples=[1])
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "names": ["step1_basic", "step1_cache_hit"],
                    "repeat": 1
                }
            ]
        }
    )


@app.post("/dev/run-checkprompts")
async def run_checkprompts(request: RunCheckPromptsRequest = Body(..., example={"names": ["step1_basic", "step1_cache_hit"], "repeat": 1})):
    """
    체크프롬프트 실행
    
    지정된 체크프롬프트를 순서대로 실행하고 결과를 파일로 저장합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        registry_path = backend_dir / "checkprompts" / "registry.json"
        
        if not registry_path.exists():
            raise HTTPException(
                status_code=404,
                detail="체크프롬프트 레지스트리를 찾을 수 없습니다."
            )
        
        # 레지스트리 로드
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        
        prompts = registry.get("prompts", {})
        
        # run_id 생성
        run_id = str(uuid.uuid4())
        checkruns_dir = backend_dir / "output" / "checkruns" / run_id
        checkruns_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        # 각 체크프롬프트 실행
        for name in request.names:
            if name not in prompts:
                results.append({
                    "name": name,
                    "status": "error",
                    "error": f"체크프롬프트를 찾을 수 없습니다: {name}"
                })
                continue
            
            prompt_data = prompts[name]
            force_fail = prompt_data.get("force_fail", False)
            
            # 반복 실행
            for repeat_idx in range(request.repeat):
                job_id = str(uuid.uuid4())
                
                try:
                    success, result, error = run_longform_script_pipeline(
                        prompt_data,
                        job_id,
                        backend_dir,
                        force_fail=force_fail
                    )
                    
                    if success:
                        status = "success"
                        cache_hit = result.get("cache_hit", False) if isinstance(result, dict) else False
                    else:
                        status = "fail"
                        cache_hit = False
                    
                    # 결과 저장
                    result_file = checkruns_dir / f"each_{name}_{repeat_idx}.json"
                    with open(result_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "name": name,
                            "repeat": repeat_idx,
                            "job_id": job_id,
                            "status": status,
                            "cache_hit": cache_hit,
                            "result": result if success else None,
                            "error": error
                        }, f, ensure_ascii=False, indent=2)
                    
                    # 리포트에서 로그/리포트 경로 가져오기
                    logs_path = backend_dir / "output" / "logs" / f"{job_id}.log"
                    reports_path = backend_dir / "output" / "reports" / f"{job_id}.json"
                    
                    results.append({
                        "name": name,
                        "repeat": repeat_idx,
                        "status": status,
                        "job_id": job_id,
                        "cache_hit": cache_hit,
                        "error": error,
                        "log_path": str(logs_path) if logs_path.exists() else None,
                        "report_path": str(reports_path) if reports_path.exists() else None
                    })
                    
                except Exception as e:
                    # 예외 발생 시에도 서버는 정상 유지
                    error_msg = str(e)
                    results.append({
                        "name": name,
                        "repeat": repeat_idx,
                        "status": "error",
                        "job_id": job_id,
                        "error": error_msg
                    })
                    
                    # 에러 결과도 저장
                    result_file = checkruns_dir / f"each_{name}_{repeat_idx}.json"
                    with open(result_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "name": name,
                            "repeat": repeat_idx,
                            "job_id": job_id,
                            "status": "error",
                            "error": error_msg
                        }, f, ensure_ascii=False, indent=2)
        
        # 요약 저장
        summary = {
            "run_id": run_id,
            "total": len(results),
            "success": sum(1 for r in results if r.get("status") == "success"),
            "fail": sum(1 for r in results if r.get("status") == "fail"),
            "error": sum(1 for r in results if r.get("status") == "error"),
            "results": results
        }
        
        summary_path = checkruns_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "ok",
            "run_id": run_id,
            "results": results,
            "summary_path": str(summary_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"체크프롬프트 실행 중 오류 발생: {str(e)}"
        )


# ==================== 실제 출력 텍스트 확인 API ====================

from backend.checkprompts.verify_output import save_verify_outputs_from_plan
from backend.utils.export_verify import export_verify_from_plan, export_verify_from_plan_file


@app.get("/verify/texts")
async def list_verify_texts():
    """
    verify 텍스트 파일 목록 조회
    
    최근 생성된 verify 파일 목록을 반환합니다.
    기존 형식(script_*.txt, scenes_*.txt)과 새로운 형식(verify/<run_id>/*) 모두 포함.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        verify_dir = backend_dir / "output" / "verify"
        
        if not verify_dir.exists():
            return {
                "status": "ok",
                "files": [],
                "export_dirs": []
            }
        
        files = []
        export_dirs = []
        
        # 1. 기존 형식: verify/*.txt
        txt_files = sorted(
            verify_dir.glob("*.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for file_path in txt_files[:50]:  # 최대 50개
            filename = file_path.name
            stat = file_path.stat()
            
            # job_id 추출
            job_id = None
            kind = None
            if filename.startswith("script_"):
                job_id = filename[len("script_"):-len(".txt")]
                kind = "script"
            elif filename.startswith("scenes_"):
                job_id = filename[len("scenes_"):-len(".txt")]
                kind = "scenes"
            
            files.append({
                "filename": filename,
                "size": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "job_id": job_id,
                "kind": kind,
                "format": "legacy"
            })
        
        # 2. 새로운 형식: verify/<run_id>/*
        for run_dir in sorted(verify_dir.iterdir(), key=lambda p: p.stat().st_mtime if p.is_dir() else 0, reverse=True):
            if not run_dir.is_dir():
                continue
            
            run_id = run_dir.name
            run_files = []
            
            for file_path in sorted(run_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
                if file_path.is_file():
                    filename = file_path.name
                    stat = file_path.stat()
                    run_files.append({
                        "filename": filename,
                        "size": stat.st_size,
                        "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "url": f"/verify/{run_id}/{filename}"
                    })
            
            if run_files:
                export_dirs.append({
                    "run_id": run_id,
                    "files": run_files,
                    "modified_time": datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat()
                })
        
        return {
            "status": "ok",
            "files": files,
            "export_dirs": export_dirs[:20]  # 최대 20개
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"verify 텍스트 목록 조회 중 오류 발생: {str(e)}"
        )


@app.get("/verify/texts/{filename}")
async def get_verify_text(filename: str):
    """
    verify 텍스트 파일 다운로드/표시 (기존 형식)
    
    path traversal 방지: .., /, \ 금지
    verify 폴더의 파일만 허용
    """
    try:
        # 보안 검증
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=400,
                detail="잘못된 파일명입니다. path traversal은 허용되지 않습니다."
            )
        
        # verify 폴더의 파일만 허용
        if not (filename.startswith("script_") or filename.startswith("scenes_")):
            raise HTTPException(
                status_code=400,
                detail="script_*.txt 또는 scenes_*.txt 파일만 허용됩니다."
            )
        
        if not filename.endswith(".txt"):
            raise HTTPException(
                status_code=400,
                detail="txt 파일만 허용됩니다."
            )
        
        backend_dir = Path(__file__).resolve().parent
        verify_dir = backend_dir / "output" / "verify"
        file_path = verify_dir / filename
        
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"파일을 찾을 수 없습니다: {filename}"
            )
        
        # 보안: verify_dir 내부인지 확인
        try:
            file_path.resolve().relative_to(verify_dir.resolve())
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail="접근이 거부되었습니다."
            )
        
        return FileResponse(
            path=str(file_path),
            media_type="text/plain; charset=utf-8",
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 조회 중 오류 발생: {str(e)}"
        )


@app.get("/verify/{run_id}/{filename}")
async def get_verify_export_file(run_id: str, filename: str):
    """
    verify export 파일 다운로드/표시 (새로운 형식)
    
    path traversal 방지: .., /, \ 금지
    verify/{run_id}/ 폴더의 파일만 허용
    """
    try:
        # 보안 검증
        if ".." in run_id or "/" in run_id or "\\" in run_id:
            raise HTTPException(
                status_code=400,
                detail="잘못된 run_id입니다. path traversal은 허용되지 않습니다."
            )
        
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=400,
                detail="잘못된 파일명입니다. path traversal은 허용되지 않습니다."
            )
        
        # 허용된 파일명만
        allowed_files = ["script.txt", "scenes.json", "prompts.txt", "chapters.txt"]
        if filename not in allowed_files:
            raise HTTPException(
                status_code=400,
                detail=f"허용되지 않은 파일명입니다. 허용: {', '.join(allowed_files)}"
            )
        
        backend_dir = Path(__file__).resolve().parent
        verify_dir = backend_dir / "output" / "verify" / run_id
        file_path = verify_dir / filename
        
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"파일을 찾을 수 없습니다: {run_id}/{filename}"
            )
        
        # 보안: verify_dir 내부인지 확인
        try:
            file_path.resolve().relative_to((backend_dir / "output" / "verify").resolve())
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail="접근이 거부되었습니다."
            )
        
        # Content-Type 결정
        if filename.endswith(".json"):
            media_type = "application/json; charset=utf-8"
        else:
            media_type = "text/plain; charset=utf-8"
        
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 조회 중 오류 발생: {str(e)}"
        )


@app.post("/verify/generate-from-plan/{video_id}")
async def generate_verify_from_plan(video_id: str):
    """
    기존 plan JSON에서 verify 텍스트 파일 생성 (백업 경로)
    
    output/plans/{video_id}.json이 있으면 그 내용을 기반으로
    script/scenes 텍스트 파일을 생성합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        plan_path = backend_dir / "output" / "plans" / f"{video_id}.json"
        
        if not plan_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"비디오 플랜을 찾을 수 없습니다: {video_id}"
            )
        
        # 플랜 로드
        video_plan = load_video_plan(plan_path)
        
        if not video_plan:
            raise HTTPException(
                status_code=500,
                detail="플랜 로드 실패"
            )
        
        # job_id는 video_id 사용 (또는 plan의 meta에서 가져오기)
        job_id = video_id
        
        # verify 텍스트 파일 생성 (새로운 export 형식)
        plan_dict = video_plan.model_dump()
        export_files = {}
        try:
            export_files = export_verify_from_plan(
                plan_dict,
                job_id,
                backend_dir / "output"
            )
            print(f"[VERIFY_EXPORT] verify 파일 생성 완료: job_id={job_id}")
        except Exception as e:
            error_msg = f"verify 파일 생성 실패: {e}"
            print(f"[VERIFY_EXPORT] ERROR: {error_msg}")
            # 에러가 있어도 응답은 반환 (500 방지)
        
        # 기존 형식도 유지
        legacy_files = {}
        try:
            legacy_files = save_verify_outputs_from_plan(
                video_plan,
                job_id,
                backend_dir / "output"
            )
        except Exception as e:
            print(f"[VERIFY_EXPORT] WARN: 기존 형식 파일 생성 실패: {e}")
        
        return {
            "status": "ok",
            "video_id": video_id,
            "job_id": job_id,
            "verify_outputs": {
                "script_url": f"/verify/texts/script_{job_id}.txt",
                "scenes_url": f"/verify/texts/scenes_{job_id}.txt",
                "export_dir": f"/verify/{job_id}/",
                "export_files": export_files
            },
            "script_path": legacy_files.get("script_path"),
            "scenes_path": legacy_files.get("scenes_path")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"verify 파일 생성 중 오류 발생: {str(e)}"
        )


@app.post("/verify/export-all-plans")
async def export_all_plans():
    """
    기존 모든 plans JSON에서 verify 파일 생성 (배치)
    
    output/plans/*.json을 모두 읽어서 verify 파일을 생성합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        plans_dir = backend_dir / "output" / "plans"
        
        if not plans_dir.exists():
            return {
                "status": "ok",
                "message": "plans 디렉토리가 없습니다.",
                "exported": []
            }
        
        exported = []
        errors = []
        
        for plan_file in plans_dir.glob("*.json"):
            try:
                video_id = plan_file.stem
                plan_data = json.load(open(plan_file, "r", encoding="utf-8"))
                
                export_files = export_verify_from_plan(
                    plan_data,
                    video_id,
                    backend_dir / "output"
                )
                
                exported.append({
                    "video_id": video_id,
                    "export_files": list(export_files.keys())
                })
                print(f"[VERIFY_EXPORT] 배치 생성 완료: video_id={video_id}")
            except Exception as e:
                error_msg = f"{plan_file.name}: {str(e)}"
                errors.append(error_msg)
                print(f"[VERIFY_EXPORT] ERROR: {error_msg}")
        
        return {
            "status": "ok",
            "exported_count": len(exported),
            "exported": exported,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"배치 생성 중 오류 발생: {str(e)}"
        )


# ==================== 2단계: 롱폼 스크립트 구조화 ====================

from backend.ai_engine.script_parser import parse_longform_script
from backend.utils.step2_exporter import export_step2_results, export_step2_error
from backend.utils.step3_converter import (
    convert_scenes_to_fixed,
    validate_fixed_spec,
    check_utf8_encoding,
    generate_step3_report,
    load_step2_result,
    convert_step2_to_step3_spec
)


class StructureScriptRequest(BaseModel):
    """스크립트 구조화 요청"""
    script: str = Field(
        ..., 
        description="롱폼 대본 문자열",
        examples=[STEP2_TEXT]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "script": STEP2_TEXT
                }
            ]
        }
    )


@app.post("/step2/structure-script")
async def structure_script(request: StructureScriptRequest = Body(..., example={"script": STEP2_TEXT})):
    """
    2단계: 롱폼 스크립트 구조화
    
    입력된 롱폼 대본을 구조화하여 파일로 저장합니다.
    """
    try:
        from backend.utils.run_manager import (
            create_run_manifest,
            find_run_by_input_hash,
            calculate_input_hash,
            is_step_completed,
            mark_step_completed,
            mark_step_failed,
            RunStep,
            get_run_subdirs,
            load_run_manifest
        )
        from backend.utils.quality_gate import check_step2_quality
        import shutil
        
        backend_dir = Path(__file__).resolve().parent
        output_dir = backend_dir / "output"
        
        # 입력 검증 및 인코딩 보장
        script_input_raw = request.script.strip() if request.script else ""
        
        # 인코딩 검증 및 복구
        from backend.utils.encoding_utils import ensure_utf8_string, validate_before_save
        
        script_input, encoding_diagnostic = ensure_utf8_string(script_input_raw, "request.script")
        input_hash = calculate_input_hash(script_input)
        
        # 인코딩 복구 사용 여부 리포트에 기록
        encoding_warnings = []
        if encoding_diagnostic.get("encoding_fallback_used"):
            encoding_warnings.append(f"encoding_fallback_used: {encoding_diagnostic.get('encoding_fallback_used')}")
        
        # 저장 전 검증
        is_valid, error_msg = validate_before_save(script_input, "script_input")
        if not is_valid:
            # Run Manifest 없이 에러 반환 (기존 방식 유지)
            run_id = str(uuid.uuid4())
            create_run_manifest(run_id, input_hash, backend_dir)
            from backend.utils.run_manifest_helper import update_manifest_step2
            update_manifest_step2(
                run_id,
                status="fail",
                files={},
                errors=[f"입력 스크립트 인코딩 검증 실패: {error_msg}"],
                warnings=[],
                base_dir=backend_dir
            )
            error_files = export_step2_error(
                run_id,
                output_dir,
                f"입력 스크립트 인코딩 검증 실패: {error_msg}"
            )
            return {
                "status": "error",
                "run_id": run_id,
                "message": f"입력 스크립트 인코딩 검증 실패: {error_msg}",
                "report_path": error_files.get("report_path")
            }
        
        if not script_input:
            # Run Manifest 없이 에러 반환 (기존 방식 유지)
            run_id = str(uuid.uuid4())
            create_run_manifest(run_id, input_hash, backend_dir)
            from backend.utils.run_manifest_helper import update_manifest_step2
            update_manifest_step2(
                run_id,
                status="fail",
                files={},
                errors=["입력 스크립트가 비어있습니다."],
                warnings=[],
                base_dir=backend_dir
            )
            error_files = export_step2_error(
                run_id,
                output_dir,
                "입력 스크립트가 비어있습니다."
            )
            return {
                "status": "error",
                "run_id": run_id,
                "message": "입력 스크립트가 비어있습니다.",
                "report_path": error_files.get("report_path")
            }
        
        # "string" placeholder 방어 로직
        if script_input.lower() == "string" or script_input == '"string"':
            run_id = str(uuid.uuid4())
            create_run_manifest(run_id, input_hash, backend_dir)
            from backend.utils.run_manifest_helper import update_manifest_step2
            update_manifest_step2(
                run_id,
                status="fail",
                files={},
                errors=["유효하지 않은 입력입니다. 'string' placeholder는 허용되지 않습니다."],
                warnings=[],
                base_dir=backend_dir
            )
            error_files = export_step2_error(
                run_id,
                output_dir,
                "유효하지 않은 입력입니다. 'string' placeholder는 허용되지 않습니다."
            )
            raise HTTPException(
                status_code=400,
                detail="유효하지 않은 입력입니다. 'string' placeholder는 허용되지 않습니다. Swagger의 'Try it out'에서 예시 값을 사용해주세요."
            )
        
        # 입력 해시 계산 및 기존 Run 확인
        input_hash = calculate_input_hash(script_input)
        existing_run_id = find_run_by_input_hash(input_hash, backend_dir)
        
        if existing_run_id:
            # 기존 Run 재사용
            run_id = existing_run_id
            print(f"[STEP2_SCRIPT] 기존 Run 재사용: run_id={run_id}")
            
            # v1.4 피드백 반영: 기존 run에도 운영 콘솔 전제 강제 (없을 때만 주입)
            from backend.utils.run_manager import update_run_manifest
            existing_manifest = load_run_manifest(run_id, backend_dir)
            if existing_manifest:
                manifest_updates_existing = {}
                if existing_manifest.get("ui_scope") is None:
                    manifest_updates_existing["ui_scope"] = "OPS_CONSOLE"
                
                if "governance" not in existing_manifest or not isinstance(existing_manifest.get("governance"), dict):
                    manifest_updates_existing["governance"] = {
                        "auto_select_enabled": False,
                        "recommendation_enabled": False
                    }
                else:
                    governance_existing = existing_manifest["governance"]
                    governance_updates_existing = {}
                    if governance_existing.get("auto_select_enabled") is None:
                        governance_updates_existing["auto_select_enabled"] = False
                    if governance_existing.get("recommendation_enabled") is None:
                        governance_updates_existing["recommendation_enabled"] = False
                    
                    if governance_updates_existing:
                        governance_existing.update(governance_updates_existing)
                        manifest_updates_existing["governance"] = governance_existing
                
                if manifest_updates_existing:
                    update_run_manifest(run_id, manifest_updates_existing, backend_dir)
            
            # Step2가 이미 완료되었는지 확인
            if is_step_completed(run_id, RunStep.STEP2, backend_dir):
                print(f"[STEP2_SCRIPT] Step2 이미 완료됨, 스킵")
                # 기존 결과 반환
                from backend.utils.output_paths import get_step2_file_paths
                step2_paths = get_step2_file_paths(run_id, backend_dir)
                report_path = step2_paths["report_json"]
                
                if report_path.exists():
                    with open(report_path, "r", encoding="utf-8") as f:
                        report_data = json.load(f)
                    
                    return {
                        "status": "success",
                        "run_id": run_id,
                        "summary": report_data.get("summary", {}),
                        "message": "Step2 이미 완료됨 (기존 결과 반환)",
                        "files": {
                            "script_txt": str(step2_paths["script_txt"]),
                            "sentences_txt": str(step2_paths["sentences_txt"]),
                            "scenes_json": str(step2_paths["scenes_json"]),
                            "report_json": str(report_path)
                        }
                    }
        else:
            # 새 Run 생성
            run_id = str(uuid.uuid4())
            print(f"[STEP2_SCRIPT] 새 Run 생성: run_id={run_id}")
            create_run_manifest(run_id, input_hash, backend_dir)
        
        # Run 디렉토리 구조 생성
        run_dirs = get_run_subdirs(run_id, backend_dir)
        # Manifest 보정 + Step2 시작 상태 기록
        from backend.utils.run_manifest_helper import update_manifest_step2
        from backend.utils.run_manager import update_run_manifest
        manifest = load_run_manifest(run_id, backend_dir)
        if manifest is None:
            manifest = create_run_manifest(run_id, input_hash, backend_dir)
        
        # v1.4 피드백 반영: Step2 실행 시 운영 콘솔 전제 강제 (없을 때만 주입)
        manifest_updates = {}
        if manifest.get("ui_scope") is None:
            manifest_updates["ui_scope"] = "OPS_CONSOLE"
        
        if "governance" not in manifest or not isinstance(manifest.get("governance"), dict):
            manifest_updates["governance"] = {
                "auto_select_enabled": False,
                "recommendation_enabled": False
            }
        else:
            governance = manifest["governance"]
            governance_updates = {}
            if governance.get("auto_select_enabled") is None:
                governance_updates["auto_select_enabled"] = False
            if governance.get("recommendation_enabled") is None:
                governance_updates["recommendation_enabled"] = False
            
            if governance_updates:
                governance.update(governance_updates)
                manifest_updates["governance"] = governance
        
        if manifest_updates:
            update_run_manifest(run_id, manifest_updates, backend_dir)
            manifest.update(manifest_updates)
        
        update_manifest_step2(
            run_id,
            status="running",
            files={},
            errors=[],
            warnings=[],
            base_dir=backend_dir
        )
        
        # 입력 파일 저장 (Run 구조 내)
        input_file_path = run_dirs["input"] / "script.txt"
        input_file_path.write_text(script_input, encoding="utf-8", newline="\n")
        
        # 스크립트 구조화
        pipeline_start = datetime.now()
        print(f"[STEP2_SCRIPT] 스크립트 구조화 시작: run_id={run_id}, 입력 길이={len(script_input)}자")
        
        # 인코딩 진단 정보 로깅
        if encoding_diagnostic.get("has_korean"):
            print(f"[STEP2_SCRIPT] 입력 한글 포함: {encoding_diagnostic.get('korean_count', 0)}자")
        if encoding_diagnostic.get("has_mojibox"):
            print(f"[STEP2_SCRIPT] WARN: 입력에 모지박 감지됨 (복구 시도됨)")
        
        parsed_data = parse_longform_script(script_input)
        
        print(f"[STEP2_SCRIPT] 파싱 완료: 문장={len(parsed_data.get('sentences', []))}개, 씬={len(parsed_data.get('scenes', []))}개")
        
        # 결과 파일 생성 (기존 위치에 저장 - 하위 호환 유지)
        created_files = export_step2_results(
            parsed_data,
            run_id,
            output_dir,
            start_time=pipeline_start,
            encoding_warnings=encoding_warnings
        )
        
        # 품질 게이트 검사
        quality_passed, quality_errors = check_step2_quality(parsed_data)
        if not quality_passed:
            error_msg = "; ".join(quality_errors)
            
            # Manifest에 실패 기록
            try:
                from backend.utils.run_manifest_helper import update_manifest_step2
                import traceback
                error_trace = traceback.format_exc()
                update_manifest_step2(
                    run_id,
                    status="fail",
                    files={},
                    errors=[error_msg, error_trace],
                    warnings=[],
                    base_dir=backend_dir
                )
            except Exception:
                pass  # Manifest 업데이트 실패해도 계속
            
            # 기존 함수 호출 (하위 호환 유지)
            mark_step_failed(run_id, RunStep.STEP2, error_msg, backend_dir)
            
            raise HTTPException(
                status_code=400,
                detail=f"Step2 품질 게이트 실패: {error_msg}"
            )
        
        # Run 구조로 파일 복사 (요구사항 스펙)
        from backend.utils.output_paths import get_step2_file_paths
        from backend.utils.run_manifest_helper import copy_step2_files_to_runs, update_manifest_step2
        
        legacy_paths = get_step2_file_paths(run_id, backend_dir)
        
        # runs/step2/ 구조로 복사
        copy_result = copy_step2_files_to_runs(run_id, legacy_paths, backend_dir)
        
        # Manifest 업데이트
        warnings_list = encoding_warnings if encoding_warnings else []
        update_manifest_step2(
            run_id,
            status="success",
            files=copy_result,
            errors=[],
            warnings=warnings_list,
            base_dir=backend_dir
        )
        
        # 기존 함수 호출 (하위 호환 유지)
        files_generated = [str(p) for p in legacy_paths.values() if p.exists()]
        mark_step_completed(run_id, RunStep.STEP2, files_generated, backend_dir)
        
        # timings 제거 (리포트에만 포함)
        timings_data = created_files.pop("_timings", {})
        
        # 요약 정보
        scenes = parsed_data.get("scenes", [])
        sentences = parsed_data.get("sentences", [])
        structure = parsed_data.get("structure", {})
        paragraphs = parsed_data.get("paragraphs", [])
        
        pipeline_end = datetime.now()
        duration_ms = round((pipeline_end - pipeline_start).total_seconds() * 1000, 2)
        
        return {
            "status": "success",
            "run_id": run_id,
            "summary": {
                "sentence_count": len(sentences),
                "scene_count": len(scenes),
                "structure": {
                    "intro_count": len(structure.get("intro", [])),
                    "body_count": len(structure.get("body", [])),
                    "transition_count": len(structure.get("transitions", [])),
                    "conclusion_count": len(structure.get("conclusion", []))
                }
            },
            "counts": {
                "sentences": len(sentences),
                "paragraphs": len(paragraphs),
                "scenes": len(scenes)
            },
            "files": {
                "script_txt": str(legacy_paths["script_txt"]),
                "sentences_txt": str(legacy_paths["sentences_txt"]),
                "scenes_json": str(legacy_paths["scenes_json"]),
                "report_json": str(legacy_paths["report_json"])
            },
            "generated_files": created_files,  # 하위 호환 유지
            "timings": {
                "start_time": pipeline_start.isoformat(),
                "end_time": pipeline_end.isoformat(),
                "duration_ms": duration_ms
            },
            "quality_gate": {
                "passed": quality_passed,
                "errors": [] if quality_passed else quality_errors
            }
        }
        
    except Exception as e:
        # 예외 발생 시에도 에러 리포트 생성 (500 방지)
        error_msg = str(e)
        print(f"[STEP2_SCRIPT] ERROR: {error_msg}")
        
        try:
            if 'run_id' in locals():
                try:
                    from backend.utils.run_manifest_helper import update_manifest_step2
                    update_manifest_step2(
                        run_id,
                        status="fail",
                        files={},
                        errors=[error_msg],
                        warnings=[],
                        base_dir=backend_dir
                    )
                except Exception:
                    pass
            # run_id와 output_dir이 정의되지 않은 경우 처리
            error_run_id = run_id if 'run_id' in locals() else str(uuid.uuid4())
            error_output_dir = output_dir if 'output_dir' in locals() else Path(__file__).resolve().parent / "output"
            
            error_files = export_step2_error(
                error_run_id,
                error_output_dir,
                error_msg
            )
            
            return {
                "status": "error",
                "run_id": error_run_id,
                "message": error_msg,
                "report_path": error_files.get("report_path")
            }
        except Exception as e2:
            # 리포트 생성도 실패한 경우
            raise HTTPException(
                status_code=500,
                detail=f"스크립트 구조화 중 오류 발생: {error_msg} (리포트 생성 실패: {str(e2)})"
        )


# ==================== Step2 디버그 진입점 ====================

class DebugStep2Request(BaseModel):
    """Step2 디버그 실행 요청"""
    text: Optional[str] = Field(
        default=None, 
        description="롱폼 대본 텍스트 (topic과 함께 제공되면 text 우선)",
        examples=[None]
    )
    topic: Optional[str] = Field(
        default=None,
        description="주제 (text가 없으면 topic 기반 임시 스크립트 생성)",
        examples=["자영업자 폐업률"]
    )
    
    @field_validator('text', 'topic', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """빈 문자열을 None으로 변환"""
        if v == '':
            return None
        return v
    
    @model_validator(mode='after')
    def validate_at_least_one(self):
        """text 또는 topic 중 하나는 필수"""
        if not self.text and not self.topic:
            raise ValueError(
                f"text 또는 topic 중 하나는 필수입니다. "
                f"예시: {{'text': '{STEP2_TEXT[:50]}...'}} 또는 {{'topic': '{STEP2_TOPIC}'}}"
            )
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "text": STEP2_TEXT,
                    "topic": None
                },
                {
                    "text": None,
                    "topic": STEP2_TOPIC
                }
            ]
        }
    )


@app.post("/debug/step2")
async def debug_step2(request: DebugStep2Request):
    """
    Step2 디버그 진입점
    
    text 또는 topic을 입력받아 Step2 파이프라인을 실행합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        output_dir = backend_dir / "output"
        
        # run_id 생성
        run_id = str(uuid.uuid4())
        
        print(f"[STEP2_SCRIPT] ===== Step2 디버그 실행 시작: run_id={run_id} =====")
        
        # 입력 검증 강화
        script_text = None
        warnings = []
        
        if request.text and request.text.strip():
            script_text = request.text.strip()
            # "string" placeholder 체크
            if script_text.lower() == "string" or script_text == '"string"':
                error_files = export_step2_error(
                    run_id,
                    output_dir,
                    "유효하지 않은 입력입니다. 'string' placeholder는 허용되지 않습니다."
                )
                raise HTTPException(
                    status_code=400,
                    detail="유효하지 않은 입력입니다. 'string' placeholder는 허용되지 않습니다."
                )
            # 길이 검증
            if len(script_text) < 50:
                warnings.append(f"입력 텍스트가 짧습니다 ({len(script_text)}자). 권장: 50자 이상.")
            print(f"[STEP2_SCRIPT] 입력: text (길이={len(script_text)}자)")
        elif request.topic and request.topic.strip():
            topic = request.topic.strip()
            # "string" placeholder 체크
            if topic.lower() == "string" or topic == '"string"':
                error_files = export_step2_error(
                    run_id,
                    output_dir,
                    "유효하지 않은 입력입니다. 'string' placeholder는 허용되지 않습니다."
                )
                raise HTTPException(
                    status_code=400,
                    detail="유효하지 않은 입력입니다. 'string' placeholder는 허용되지 않습니다."
                )
            # topic 기반 임시 스크립트 생성
            script_text = f"""안녕하세요. 오늘은 {topic}에 대해 이야기해보겠습니다.

많은 분들이 {topic}에 대해 궁금해하시는데요. 실제로 이 주제는 우리 일상과 밀접한 관련이 있습니다.

먼저 {topic}의 기본 개념부터 살펴보겠습니다. 이는 매우 중요한 요소입니다.

다음으로 {topic}의 실제 사례를 통해 더 깊이 이해해보겠습니다. 여러분도 한 번쯤 경험해보셨을 것입니다.

마지막으로 {topic}에 대한 핵심 요약과 앞으로의 전망을 정리해보겠습니다.

이상으로 {topic}에 대한 이야기를 마치겠습니다. 감사합니다."""
            print(f"[STEP2_SCRIPT] 입력: topic={topic} (임시 스크립트 생성, 길이={len(script_text)}자)")
        else:
            # 에러 리포트 생성 (500 방지)
            error_files = export_step2_error(
                run_id,
                output_dir,
                "text 또는 topic 중 하나는 필수입니다."
            )
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "validation_error",
                    "message": "text 또는 topic 중 하나는 필수입니다.",
                    "hint": "다음 중 하나를 입력하세요:\n- text: 롱폼 대본 텍스트 (예: '안녕하세요. 오늘은...')\n- topic: 주제 (예: '자영업자 폐업률')",
                    "examples": {
                    "text_example": STEP2_TEXT[:100] + "...",
                    "topic_example": STEP2_TOPIC
                    }
                }
            )
        
        # Step2 파이프라인 실행
        pipeline_start = datetime.now()
        print(f"[STEP2_SCRIPT] 스크립트 구조화 시작")
        
        # 인코딩 검증 및 복구 (디버그 엔드포인트용)
        from backend.utils.encoding_utils import ensure_utf8_string, validate_before_save
        script_text_fixed, encoding_diagnostic = ensure_utf8_string(script_text, "debug_step2.script_text")
        encoding_warnings = []
        if encoding_diagnostic.get("encoding_fallback_used"):
            encoding_warnings.append(f"encoding_fallback_used: {encoding_diagnostic.get('encoding_fallback_used')}")
        
        # 저장 전 검증
        is_valid, error_msg = validate_before_save(script_text_fixed, "script_text")
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"입력 스크립트 인코딩 검증 실패: {error_msg}"
            )
        
        parsed_data = parse_longform_script(script_text_fixed)
        
        print(f"[STEP2_SCRIPT] 파싱 완료: 문장={len(parsed_data.get('sentences', []))}개, 씬={len(parsed_data.get('scenes', []))}개")
        
        # 결과 파일 생성 (인코딩 경고 전달)
        created_files = export_step2_results(
            parsed_data,
            run_id,
            output_dir,
            start_time=pipeline_start,
            encoding_warnings=encoding_warnings
        )
        
        # warnings가 있으면 로그에 기록
        if warnings:
            for warning in warnings:
                print(f"[STEP2_SCRIPT] WARN: {warning}")
        
        # timings 제거 (리포트에만 포함)
        timings_data = created_files.pop("_timings", {})
        
        # 요약 정보
        scenes = parsed_data.get("scenes", [])
        sentences = parsed_data.get("sentences", [])
        structure = parsed_data.get("structure", {})
        paragraphs = parsed_data.get("paragraphs", [])
        
        pipeline_end = datetime.now()
        duration_ms = round((pipeline_end - pipeline_start).total_seconds() * 1000, 2)
        
        return {
            "status": "success",
            "run_id": run_id,
            "summary": {
                "sentence_count": len(sentences),
                "scene_count": len(scenes),
                "structure": {
                    "intro_count": len(structure.get("intro", [])),
                    "body_count": len(structure.get("body", [])),
                    "transition_count": len(structure.get("transitions", [])),
                    "conclusion_count": len(structure.get("conclusion", []))
                }
            },
            "counts": {
                "sentences": len(sentences),
                "paragraphs": len(paragraphs),
                "scenes": len(scenes)
            },
            "generated_files": created_files,
            "timings": {
                "start_time": pipeline_start.isoformat(),
                "end_time": pipeline_end.isoformat(),
                "duration_ms": duration_ms
            }
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[STEP2_SCRIPT] ERROR: {error_msg}")
        
        try:
            error_run_id = run_id if 'run_id' in locals() else str(uuid.uuid4())
            error_output_dir = output_dir if 'output_dir' in locals() else Path(__file__).resolve().parent / "output"
            
            error_files = export_step2_error(
                error_run_id,
                error_output_dir,
                error_msg
            )
            
            return {
                "status": "error",
                "run_id": error_run_id,
                "message": error_msg,
                "report_path": error_files.get("report_path")
            }
        except Exception as e2:
            raise HTTPException(
                status_code=500,
                detail=f"Step2 실행 중 오류 발생: {error_msg} (리포트 생성 실패: {str(e2)})"
            )


# ==================== 3단계: Scene JSON 고정 스펙 변환 ====================

class Step3ConvertRequest(BaseModel):
    """Step 3 변환 요청"""
    run_id: str = Field(
        ...,
        description="Step 2에서 생성된 run_id",
        examples=["d2f1ed8b-0e8a-46a8-8741-798e974ba219"]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "run_id": "d2f1ed8b-0e8a-46a8-8741-798e974ba219"
                }
            ]
        }
    )


@app.post("/step3/convert-to-fixed-spec")
async def convert_to_step3_spec(request: Step3ConvertRequest = Body(..., example={"run_id": "965d3860-66e9-401d-b0ed-fd068186ff89"})):
    """
    3단계: Scene JSON 고정 스펙 변환
    
    Step 2의 결과를 Step 3 고정 스펙으로 변환하여 저장합니다.
    """
    try:
        backend_dir = Path(__file__).resolve().parent
        output_dir = backend_dir / "output"
        
        run_id = request.run_id
        
        print(f"[STEP3_CONVERT] 변환 시작: run_id={run_id}")
        
        # Manifest 존재 보장 + Step3 상태 running으로 전환
        from backend.utils.run_manager import load_run_manifest, create_run_manifest
        from backend.utils.run_manifest_helper import update_manifest_step3
        manifest = load_run_manifest(run_id, backend_dir)
        if manifest is None:
            manifest = create_run_manifest(run_id, None, backend_dir)
        elif manifest.get("steps", {}).get("step2", {}).get("status") != "success":
            raise HTTPException(
                status_code=400,
                detail="Step2가 완료되지 않았습니다. Step2 완료 후 Step3를 실행하세요."
            )
        update_manifest_step3(
            run_id,
            status="running",
            files={},
            errors=[],
            warnings=[],
            base_dir=backend_dir
        )
        
        # Step 2 결과 로드
        step2_data = load_step2_result(run_id, output_dir)
        if step2_data is None:
            update_manifest_step3(
                run_id,
                status="fail",
                files={},
                errors=[f"Step 2 결과를 찾을 수 없습니다: run_id={run_id}"],
                warnings=[],
                base_dir=backend_dir
            )
            raise HTTPException(
                status_code=404,
                detail=f"Step 2 결과를 찾을 수 없습니다: run_id={run_id}"
            )
        
        print(f"[STEP3_CONVERT] Step 2 결과 로드 완료: 씬 {len(step2_data.get('scenes', []))}개")
        
        # 파일 경로 생성 (통합 유틸 사용)
        from backend.utils.output_paths import get_step2_file_paths, get_step3_file_paths
        
        step2_paths = get_step2_file_paths(run_id, backend_dir)
        step3_paths = get_step3_file_paths(run_id, backend_dir)
        input_scenes_path = step2_paths["scenes_json"]
        output_scenes_fixed_path = step3_paths["scenes_fixed_json"]
        
        # 변환 실행
        fixed_data = convert_scenes_to_fixed(
            str(input_scenes_path),
            str(output_scenes_fixed_path),
            style_profile="default"
        )
        
        print(f"[STEP3_CONVERT] 변환 완료: 씬 {len(fixed_data.get('scenes', []))}개")
        
        # 검증
        validation_result = validate_fixed_spec(fixed_data)
        is_valid, missing_required, forbidden_found = validation_result
        
        if not is_valid:
            error_msg = f"필수 필드 누락: {len(missing_required)}개, 금지 필드 발견: {len(forbidden_found)}개"
            
            # Manifest에 실패 기록
            try:
                from backend.utils.run_manifest_helper import update_manifest_step3
                import traceback
                error_trace = traceback.format_exc()
                update_manifest_step3(
                    run_id,
                    status="fail",
                    files={},
                    errors=[error_msg, error_trace],
                    warnings=[],
                    base_dir=backend_dir
                )
            except Exception:
                pass  # Manifest 업데이트 실패해도 계속
            
            raise HTTPException(
                status_code=400,
                detail=f"Step 3 스펙 검증 실패: {error_msg}"
            )
        
        print(f"[STEP3_CONVERT] 검증 통과")
        
        # UTF-8 인코딩 검증
        encoding_check = check_utf8_encoding(str(output_scenes_fixed_path))
        encoding_valid, encoding_error = encoding_check
        
        if not encoding_valid:
            raise HTTPException(
                status_code=500,
                detail=f"UTF-8 인코딩 검증 실패: {encoding_error}"
            )
        
        # 리포트 생성
        report_path = generate_step3_report(
            str(input_scenes_path),
            str(output_scenes_fixed_path),
            fixed_data,
            validation_result,
            encoding_check,
            run_id,
            output_dir
        )
        
        print(f"[STEP3_CONVERT] 리포트 생성 완료: {report_path}")
        
        # Run 구조로 파일 복사 (요구사항 스펙)
        from backend.utils.run_manifest_helper import copy_step3_files_to_runs, update_manifest_step3
        
        legacy_step3_paths = {
            "scenes_fixed_json": output_scenes_fixed_path,
            "report_json": report_path
        }
        
        # runs/step3/ 구조로 복사
        copy_result = copy_step3_files_to_runs(run_id, legacy_step3_paths, backend_dir)
        
        # Manifest 업데이트
        update_manifest_step3(
            run_id,
            status="success",
            files=copy_result,
            errors=[],
            warnings=[],
            base_dir=backend_dir
        )
        
        return {
            "status": "success",
            "run_id": run_id,
            "output_file": str(output_scenes_fixed_path),
            "report_file": str(report_path),
            "scenes_count": len(fixed_data.get("scenes", []))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[STEP3_CONVERT] ERROR: {error_msg}")
        
        # Manifest에 실패 기록
        try:
            from backend.utils.run_manifest_helper import update_manifest_step3
            import traceback
            error_trace = traceback.format_exc()
            update_manifest_step3(
                run_id,
                status="fail",
                files={},
                errors=[error_msg, error_trace],
                warnings=[],
                base_dir=backend_dir
            )
        except Exception:
            pass  # Manifest 업데이트 실패해도 계속
        
        raise HTTPException(
            status_code=500,
            detail=f"Step 3 변환 중 오류 발생: {error_msg}"
        )


# ==================== Step3 디버그 엔드포인트 ====================

class DebugStep3Request(BaseModel):
    """Step 3 디버그 실행 요청"""
    run_id: Optional[str] = Field(
        default=None,
        description="Step 2에서 생성된 run_id (use_latest=true면 무시)",
        examples=["d2f1ed8b-0e8a-46a8-8741-798e974ba219"]
    )
    style_profile: Optional[str] = Field(
        default="default",
        description="스타일 프로필 이름",
        examples=["default"]
    )
    use_latest: Optional[bool] = Field(
        default=False,
        description="최신 scenes.json 사용 여부 (true면 run_id 무시)",
        examples=[False]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "run_id": "d2f1ed8b-0e8a-46a8-8741-798e974ba219",
                    "style_profile": "default",
                    "use_latest": False
                }
            ]
        }
    )


@app.post("/debug/step3")
async def debug_step3(request: DebugStep3Request):
    """
    3단계: Scene JSON 고정 스펙 변환 (디버그 엔드포인트)
    
    Step 2의 구형 scenes.json을 고정 스펙 scenes_fixed.json으로 변환합니다.
    """
    try:
        from backend.utils.output_paths import get_output_dirs, get_step3_file_paths
        
        backend_dir = Path(__file__).resolve().parent
        dirs = get_output_dirs(backend_dir)
        output_dir = dirs["root"]
        plans_dir = dirs["plans"]
        
        # 입력 파일 경로 결정
        if request.use_latest:
            # 최신 scenes.json 찾기
            scenes_files = sorted(
                plans_dir.glob("*_scenes.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if not scenes_files:
                raise HTTPException(
                    status_code=404,
                    detail="최신 scenes.json 파일을 찾을 수 없습니다"
                )
            input_scenes_path = scenes_files[0]
            # 파일명에서 run_id 추출
            run_id = input_scenes_path.stem.replace("_scenes", "")
        else:
            if not request.run_id:
                raise HTTPException(
                    status_code=400,
                    detail="run_id 또는 use_latest=true가 필요합니다"
                )
            run_id = request.run_id
            input_scenes_path = plans_dir / f"{run_id}_scenes.json"
            if not input_scenes_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Step 2 결과를 찾을 수 없습니다: run_id={run_id}"
                )
        
        print(f"[DEBUG_STEP3] 변환 시작: run_id={run_id}, input={input_scenes_path}")
        
        # 출력 파일 경로 (통합 유틸 사용)
        file_paths = get_step3_file_paths(run_id, backend_dir)
        output_scenes_fixed_path = file_paths["scenes_fixed_json"]
        
        # 변환 실행
        fixed_data = convert_scenes_to_fixed(
            str(input_scenes_path),
            str(output_scenes_fixed_path),
            style_profile=request.style_profile or "default"
        )
        
        print(f"[DEBUG_STEP3] 변환 완료: 씬 {len(fixed_data.get('scenes', []))}개")
        
        # 검증
        validation_result = validate_fixed_spec(fixed_data)
        is_valid, missing_required, forbidden_found = validation_result
        
        print(f"[DEBUG_STEP3] 검증 결과: valid={is_valid}, missing={len(missing_required)}, forbidden={len(forbidden_found)}")
        
        # UTF-8 인코딩 검증
        encoding_check = check_utf8_encoding(str(output_scenes_fixed_path))
        encoding_valid, encoding_error = encoding_check
        
        print(f"[DEBUG_STEP3] UTF-8 검증: valid={encoding_valid}")
        
        # 리포트 생성
        report_path = generate_step3_report(
            str(input_scenes_path),
            str(output_scenes_fixed_path),
            fixed_data,
            validation_result,
            encoding_check,
            run_id,
            output_dir
        )
        
        print(f"[DEBUG_STEP3] 리포트 생성 완료: {report_path}")
        
        # 전체 상태 결정
        overall_status = "success" if (is_valid and encoding_valid) else "fail"
        
        return {
            "status": overall_status,
            "run_id": run_id,
            "input_file": str(input_scenes_path),
            "output_file": str(output_scenes_fixed_path),
            "report_file": str(report_path),
            "counts": {
                "scenes_count": len(fixed_data.get("scenes", []))
            },
            "schema_check": {
                "passed": is_valid,
                "missing_required": missing_required,
                "forbidden_found": forbidden_found
            },
            "encoding_check": {
                "utf8_readable": encoding_valid,
                "error": encoding_error
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        import traceback
        error_trace = traceback.format_exc()
        print(f"[DEBUG_STEP3] ERROR: {error_msg}\n{error_trace}")
        
        # 리포트에 에러 기록 (가능한 경우)
        try:
            backend_dir = Path(__file__).resolve().parent
            output_dir = backend_dir / "output"
            reports_dir = output_dir / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            error_run_id = request.run_id if request.run_id else "unknown"
            error_report_path = reports_dir / f"{error_run_id}_step3_report.json"
            
            error_report = {
                "run_id": error_run_id,
                "generated_at": datetime.now().isoformat(),
                "step": 3,
                "status": "fail",
                "errors": [error_msg, error_trace]
            }
            
            with open(error_report_path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(error_report, f, ensure_ascii=False, indent=2)
        except:
            pass  # 리포트 생성 실패해도 무시
        
        raise HTTPException(
            status_code=500,
            detail=f"Step 3 변환 중 오류 발생: {error_msg}"
        )


# ==================== 인코딩 디버그 엔드포인트 ====================

@app.get("/debug/encoding", include_in_schema=False)
async def debug_encoding():
    """
    인코딩 정보 확인 엔드포인트
    
    시스템 인코딩 설정 및 샘플 텍스트를 반환합니다.
    """
    from backend.utils.encoding_utils import get_encoding_info, ensure_utf8_string
    
    encoding_info = get_encoding_info()
    
    # 샘플 텍스트 테스트
    sample_text = "한글 테스트: 안녕하세요"
    sample_fixed, sample_diagnostic = ensure_utf8_string(sample_text, "sample")
    
    return {
        "ok": True,
        "sample": sample_fixed,
        "sample_diagnostic": sample_diagnostic,
        "python": sys.version.split()[0],
        "fs_encoding": encoding_info.get("filesystem_encoding"),
        "preferred_encoding": encoding_info.get("preferred_encoding"),
        "encoding_info": encoding_info
    }


class Step2QuickCheckRequest(BaseModel):
    """Step2 빠른 검증 요청"""
    text: str = Field(
        ...,
        description="검증할 텍스트 (한글 포함)",
        examples=["안녕하세요. 오늘은 좋은 날입니다."]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "text": "안녕하세요. 오늘은 좋은 날입니다. 테스트를 진행하겠습니다."
                }
            ]
        }
    )


@app.post("/debug/step2/quickcheck", include_in_schema=False)
async def debug_step2_quickcheck(request: Step2QuickCheckRequest):
    """
    Step2 빠른 검증 엔드포인트
    
    입력 텍스트를 Step2 파이프라인으로 처리하고,
    저장 후 다시 읽어서 한글이 유지되는지 확인합니다.
    """
    try:
        from backend.ai_engine.script_parser import parse_longform_script
        from backend.utils.encoding_utils import (
            ensure_utf8_string,
            validate_before_save,
            has_korean,
            detect_mojibox,
            count_korean_chars
        )
        
        backend_dir = Path(__file__).resolve().parent
        output_dir = backend_dir / "output"
        temp_dir = output_dir / "temp_quickcheck"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 입력 텍스트 인코딩 보장
        input_text_raw = request.text
        input_text, input_diagnostic = ensure_utf8_string(input_text_raw, "input")
        
        # 저장 전 검증
        is_valid, error_msg = validate_before_save(input_text, "input_text")
        if not is_valid:
            return {
                "status": "fail",
                "error": f"입력 검증 실패: {error_msg}",
                "input_diagnostic": input_diagnostic
            }
        
        # Step2 파이프라인 실행
        parsed_data = parse_longform_script(input_text)
        
        # 임시 파일 저장
        temp_script_path = temp_dir / "temp_script.txt"
        temp_sentences_path = temp_dir / "temp_sentences.txt"
        
        # script.txt 저장 및 읽기 테스트
        temp_script_path.write_text(input_text, encoding="utf-8", newline="\n")
        script_readback = temp_script_path.read_text(encoding="utf-8")
        
        # sentences.txt 저장 및 읽기 테스트
        sentences = parsed_data.get("sentences", [])
        with open(temp_sentences_path, "w", encoding="utf-8", newline="\n") as f:
            for sent in sentences:
                f.write(f"{sent['text']}\n")
        
        sentences_readback = []
        with open(temp_sentences_path, "r", encoding="utf-8") as f:
            sentences_readback = [line.strip() for line in f if line.strip()]
        
        # 검증 결과
        input_has_korean = has_korean(input_text)
        input_korean_count = count_korean_chars(input_text)
        script_readback_has_korean = has_korean(script_readback)
        script_readback_korean_count = count_korean_chars(script_readback)
        
        sentences_has_korean = any(has_korean(s) for s in sentences_readback)
        sentences_korean_count = sum(count_korean_chars(s) for s in sentences_readback)
        
        # 모지박 검사
        input_has_mojibox, _ = detect_mojibox(input_text)
        script_readback_has_mojibox, _ = detect_mojibox(script_readback)
        sentences_has_mojibox = any(detect_mojibox(s)[0] for s in sentences_readback)
        
        # 결과 비교
        script_match = input_text == script_readback
        sentences_match = len(sentences) == len(sentences_readback) and all(
            sent["text"] == read for sent, read in zip(sentences, sentences_readback)
        )
        
        # 임시 파일 정리
        try:
            temp_script_path.unlink()
            temp_sentences_path.unlink()
            temp_dir.rmdir()
        except:
            pass
        
        # 전체 상태
        overall_ok = (
            script_match and
            sentences_match and
            not input_has_mojibox and
            not script_readback_has_mojibox and
            not sentences_has_mojibox and
            input_has_korean == script_readback_has_korean and
            input_korean_count == script_readback_korean_count
        )
        
        return {
            "status": "success" if overall_ok else "fail",
            "input": {
                "length": len(input_text),
                "has_korean": input_has_korean,
                "korean_count": input_korean_count,
                "has_mojibox": input_has_mojibox,
                "diagnostic": input_diagnostic
            },
            "script_txt": {
                "match": script_match,
                "has_korean": script_readback_has_korean,
                "korean_count": script_readback_korean_count,
                "has_mojibox": script_readback_has_mojibox
            },
            "sentences_txt": {
                "count": len(sentences),
                "match": sentences_match,
                "has_korean": sentences_has_korean,
                "korean_count": sentences_korean_count,
                "has_mojibox": sentences_has_mojibox
            },
            "overall": {
                "ok": overall_ok,
                "korean_preserved": input_has_korean == script_readback_has_korean,
                "no_mojibox": not input_has_mojibox and not script_readback_has_mojibox and not sentences_has_mojibox
            }
        }
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return {
            "status": "error",
            "error": str(e),
            "traceback": error_trace
        }


# ==================== Runs 관리 API ====================

class StepState(BaseModel):
    status: str
    artifacts: List[str] = []
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    
    model_config = ConfigDict(extra="allow")


class RunResponse(BaseModel):
    """Run 응답 모델"""
    run_id: str
    created_at: str
    last_updated: Optional[str] = ""
    status: str
    steps: Dict[str, StepState] = {}
    current_step: Optional[str] = None
    completed_steps: Optional[List[str]] = []
    input_hash: Optional[str] = ""
    files_generated: Optional[List[str]] = []
    last_error: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "run_id": "d2f1ed8b-0e8a-46a8-8741-798e974ba219",
                    "created_at": "2024-01-01T00:00:00",
                    "last_updated": "2024-01-01T00:01:00",
                    "status": "running",
                    "steps": {
                        "step1": {"status": "success", "artifacts": []},
                        "step2": {"status": "running", "artifacts": []},
                        "step3": {"status": "pending", "artifacts": []}
                    },
                    "current_step": "step2",
                    "completed_steps": ["step1"],
                    "input_hash": "abc123def456",
                    "files_generated": [],
                    "last_error": None
                }
            ]
        }
    )


@app.get("/runs", response_model=List[RunResponse])
async def list_runs(
    status: Optional[str] = Query(None, description="상태 필터 (running|failed|completed)", examples=["running"]),
    limit: int = Query(50, description="최대 반환 개수", examples=[50], ge=1, le=100)
):
    """
    Run 목록 조회
    
    모든 Run의 Manifest를 조회하여 목록을 반환합니다.
    """
    try:
        from backend.utils.run_manager import load_run_manifest, get_runs_root
        
        runs_dir = get_runs_root()
        
        if not runs_dir.exists():
            return []
        
        runs = []
        for run_dir in runs_dir.iterdir():
            if not run_dir.is_dir():
                continue
            
            manifest = load_run_manifest(run_dir.name, None)
            if manifest is None:
                continue
            
            # 상태 필터 적용
            if status and manifest.get("status") != status:
                continue
            
            runs.append(RunResponse(**manifest))
        
        # 생성 시간 기준 내림차순 정렬
        runs.sort(key=lambda r: r.created_at, reverse=True)
        
        # Limit 적용
        return runs[:limit]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Run 목록 조회 실패: {str(e)}"
        )


@app.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str):
    """
    Run 상세 조회
    
    특정 Run의 Manifest를 조회합니다.
    """
    try:
        from backend.utils.run_manager import load_run_manifest
        
        backend_dir = Path(__file__).resolve().parent
        manifest = load_run_manifest(run_id, backend_dir)
        
        if manifest is None:
            raise HTTPException(
                status_code=404,
                detail=f"Run을 찾을 수 없습니다: {run_id}"
            )
        
        return RunResponse(**manifest)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Run 조회 실패: {str(e)}"
        )


class ResumeRequest(BaseModel):
    """Run 재개 요청"""
    force: bool = Field(
        default=False,
        description="강제 재개 (완료된 step도 재실행)",
        examples=[False]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "force": False
                }
            ]
        }
    )


@app.post("/runs/{run_id}/resume")
async def resume_run(run_id: str, request: ResumeRequest = ResumeRequest()):
    """
    Run 재개
    
    실패한 Run을 재개합니다. 실패한 step부터 자동으로 재실행됩니다.
    """
    try:
        from backend.utils.run_manager import load_run_manifest, get_resume_step, RunStatus
        
        backend_dir = Path(__file__).resolve().parent
        manifest = load_run_manifest(run_id, backend_dir)
        
        if manifest is None:
            raise HTTPException(
                status_code=404,
                detail=f"Run을 찾을 수 없습니다: {run_id}"
            )
        
        if manifest.get("status") == RunStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400,
                detail="이미 완료된 Run입니다"
            )
        
        # 재개할 step 확인
        resume_step = get_resume_step(run_id, backend_dir)
        if resume_step is None:
            # 모든 step 완료
            return {
                "status": "success",
                "message": "모든 step이 완료되었습니다",
                "run_id": run_id
            }
        
        # 재개 step 정보 반환 (실제 실행은 해당 step API에서 처리)
        return {
            "status": "success",
            "message": f"Run 재개 준비 완료: {resume_step.value}부터 재실행",
            "run_id": run_id,
            "resume_step": resume_step.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Run 재개 실패: {str(e)}"
        )


@app.get("/runs/latest")
async def get_latest_run():
    """
    최신 Run 조회
    
    가장 최근에 생성된 Run의 manifest를 반환합니다.
    """
    try:
        from backend.utils.run_manager import load_run_manifest, get_runs_root
        
        runs_dir = get_runs_root()
        
        if not runs_dir.exists():
            raise HTTPException(
                status_code=404,
                detail="Run이 없습니다"
            )
        
        # 모든 run 디렉토리 검색
        runs = []
        for run_dir in runs_dir.iterdir():
            if not run_dir.is_dir():
                continue
            
            manifest = load_run_manifest(run_dir.name, None)
            if manifest:
                runs.append((manifest.get("created_at", ""), manifest))
        
        if not runs:
            raise HTTPException(
                status_code=404,
                detail="Run이 없습니다"
            )
        
        # 생성 시간 기준 내림차순 정렬
        runs.sort(key=lambda x: x[0], reverse=True)
        latest_manifest = runs[0][1]
        
        return {
            "status": "success",
            "run_id": latest_manifest.get("run_id"),
            "manifest": latest_manifest
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"최신 Run 조회 실패: {str(e)}"
        )


@app.get("/runs/{run_id}/manifest")
async def get_run_manifest_endpoint(run_id: str):
    """
    Run Manifest 조회
    
    특정 Run의 manifest.json을 반환합니다.
    """
    try:
        from backend.utils.run_manager import load_run_manifest
        
        backend_dir = Path(__file__).resolve().parent
        manifest = load_run_manifest(run_id, backend_dir)
        
        if manifest is None:
            raise HTTPException(
                status_code=404,
                detail=f"Run을 찾을 수 없습니다: {run_id}"
            )
        
        return {
            "status": "success",
            "run_id": run_id,
            "manifest": manifest
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Run Manifest 조회 실패: {str(e)}"
        )


@app.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """
    Run 취소
    
    실행 중인 Run을 취소합니다.
    """
    try:
        from backend.utils.run_manager import load_run_manifest, update_run_manifest, RunStatus
        
        backend_dir = Path(__file__).resolve().parent
        manifest = load_run_manifest(run_id, backend_dir)
        
        if manifest is None:
            raise HTTPException(
                status_code=404,
                detail=f"Run을 찾을 수 없습니다: {run_id}"
            )
        
        if manifest.get("status") == RunStatus.COMPLETED.value:
            raise HTTPException(
                status_code=400,
                detail="이미 완료된 Run은 취소할 수 없습니다"
            )
        
        # 상태를 failed로 변경
        update_run_manifest(
            run_id,
            {
                "status": RunStatus.FAILED.value,
                "last_error": {
                    "step": manifest.get("current_step"),
                    "message": "사용자에 의해 취소됨",
                    "timestamp": datetime.now().isoformat()
                }
            },
            backend_dir
        )
        
        return {
            "status": "success",
            "message": "Run이 취소되었습니다",
            "run_id": run_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Run 취소 실패: {str(e)}"
        )


@app.get("/metrics/latest")
async def get_latest_metrics():
    """
    최신 Run의 메트릭 조회 (v6-Step8)
    
    가장 최근에 생성된 Run의 metrics.json을 반환합니다.
    """
    try:
        from backend.utils.metrics_store import latest_run_id, load_metrics
        
        run_id = latest_run_id()
        
        if not run_id:
            raise HTTPException(
                status_code=404,
                detail="Run이 없습니다"
            )
        
        metrics = load_metrics(run_id, None)
        
        if not metrics:
            raise HTTPException(
                status_code=404,
                detail=f"Metrics를 찾을 수 없습니다: {run_id}"
            )
        
        return {
            "status": "success",
            "run_id": run_id,
            "metrics": metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"최신 메트릭 조회 실패: {str(e)}"
        )


@app.get("/metrics/by-run/{run_id}")
async def get_metrics_by_run(run_id: str):
    """
    특정 Run의 메트릭 조회 (v6-Step8)
    
    Args:
        run_id: Run ID
    
    Returns:
        메트릭 데이터
    """
    try:
        from backend.utils.metrics_store import load_metrics
        
        metrics = load_metrics(run_id, None)
        
        if not metrics:
            raise HTTPException(
                status_code=404,
                detail=f"Metrics를 찾을 수 없습니다: {run_id}"
            )
        
        return {
            "status": "success",
            "run_id": run_id,
            "metrics": metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"메트릭 조회 실패: {str(e)}"
        )


class RollbackRequest(BaseModel):
    """Rollback 요청"""
    rollback_reason: str = Field(
        ...,
        description="롤백 사유 (필수)",
        examples=["Policy regression detected"]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "rollback_reason": "Policy regression detected"
                }
            ]
        }
    )


@app.post("/v4/rollback/{policy_version_id}")
async def rollback_policy(policy_version_id: str, request: RollbackRequest):
    """
    v4 Rollback 원클릭
    
    Args:
        policy_version_id: Policy Version ID
        request: Rollback 요청 (rollback_reason 필수)
    
    Returns:
        Rollback 결과
    """
    try:
        from backend.utils.run_manager import load_run_manifest, append_decision_trace
        from backend.evolution_v4.rollback_store import ensure_directories
        from pathlib import Path
        
        backend_dir = Path(__file__).resolve().parent
        project_root = backend_dir.parent
        
        # rollback manifest 찾기
        _, rollbacks_dir = ensure_directories(project_root)
        
        # policy_version_id에서 run_id 추출 시도
        # policy_version_id 형식: "policy_v4_step3:<candidate_id>:<n>" 또는 직접 run_id
        run_id = None
        
        # rollbacks 디렉토리에서 rollback manifest 검색
        rollback_files = list(rollbacks_dir.glob("*_rollback_manifest.json"))
        
        for rollback_file in rollback_files:
            try:
                with open(rollback_file, "r", encoding="utf-8-sig") as f:
                    rollback_manifest = json.load(f)
                
                if rollback_manifest.get("policy_version_id") == policy_version_id:
                    run_id = rollback_manifest.get("run_id")
                    break
            except Exception:
                continue
        
        if not run_id:
            # policy_version_id가 직접 run_id일 수도 있음
            run_id = policy_version_id
        
        # manifest 로드
        manifest = load_run_manifest(run_id, None)
        if manifest is None:
            raise HTTPException(
                status_code=404,
                detail=f"Run을 찾을 수 없습니다: {run_id}"
            )
        
        # v6-Step11: decision_trace에 rollback 기록 (대안>=2 포함)
        from backend.steps.v6_gates import append_decision_trace as v6_append_decision_trace
        
        rollback_entry = {
            "input_reference": f"policy_version_id={policy_version_id}",
            "alternatives": [
                {"option": "keep_current", "description": "현재 정책 유지"},
                {"option": "rollback", "description": f"롤백: {request.rollback_reason}"}
            ],
            "decision_reason": request.rollback_reason,
            "final_choice": "rollback"
        }
        
        v6_append_decision_trace(manifest, rollback_entry)
        
        # manifest 저장
        from backend.utils.run_manager import _atomic_write_json, get_run_dir
        run_dir = get_run_dir(run_id, None)
        manifest_path = run_dir / "manifest.json"
        _atomic_write_json(manifest_path, manifest)
        
        return {
            "status": "success",
            "message": "Rollback이 기록되었습니다",
            "run_id": run_id,
            "policy_version_id": policy_version_id,
            "rollback_reason": request.rollback_reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Rollback 실패: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # 로컬 개발용 실행 예시:
    # - PC에서만 확인: host="127.0.0.1"
    # - 같은 Wi-Fi의 폰/태블릿에서도 접속: host="0.0.0.0"
    #   예) python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)

