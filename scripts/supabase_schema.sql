-- KAS Studio — Supabase PostgreSQL 스키마
-- 사용법: Supabase Dashboard > SQL Editor > 이 파일 내용 붙여넣기 후 실행

-- ── 1. 채널 레지스트리 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS channels (
  id                      TEXT PRIMARY KEY,
  category                TEXT NOT NULL,
  category_ko             TEXT,
  youtube_channel_id      TEXT,
  launch_phase            INT  DEFAULT 1,
  status                  TEXT DEFAULT 'active',
  rpm_proxy               INT  DEFAULT 2,
  revenue_target_monthly  INT  DEFAULT 2000000,
  monthly_longform_target INT,
  monthly_shorts_target   INT,
  subscriber_count        INT  DEFAULT 0,
  video_count             INT  DEFAULT 0,
  algorithm_trust_level   TEXT DEFAULT 'PRE-ENTRY',
  updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ── 2. 파이프라인 실행 이력 ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id           TEXT PRIMARY KEY,
  channel_id   TEXT REFERENCES channels(id),
  run_state    TEXT,
  topic_title  TEXT,
  topic_category TEXT,
  topic_score  REAL,
  is_trending  BOOLEAN DEFAULT FALSE,
  created_at   TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

-- ── 3. 48시간 KPI ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kpi_48h (
  id                    SERIAL PRIMARY KEY,
  run_id                TEXT REFERENCES pipeline_runs(id),
  channel_id            TEXT REFERENCES channels(id),
  video_id              TEXT,
  impressions           INT,
  ctr                   REAL,
  views                 INT,
  avg_view_percentage   REAL,
  avg_view_duration_sec INT,
  algorithm_stage       TEXT,
  ctr_level             TEXT,
  collected_at          TIMESTAMPTZ
);

-- ── 4. 월별 수익 ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS revenue_monthly (
  id                  SERIAL PRIMARY KEY,
  channel_id          TEXT REFERENCES channels(id),
  month               TEXT,
  adsense_krw         REAL DEFAULT 0,
  affiliate_krw       REAL DEFAULT 0,
  operating_cost      REAL DEFAULT 0,
  net_profit          REAL DEFAULT 0,
  target_achieved     BOOLEAN DEFAULT FALSE,
  mix_ratio_adsense   REAL,
  mix_ratio_affiliate REAL,
  updated_at          TIMESTAMPTZ,
  UNIQUE(channel_id, month)
);

-- ── 5. 리스크 대시보드 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_monthly (
  id           SERIAL PRIMARY KEY,
  channel_id   TEXT REFERENCES channels(id),
  month        TEXT,
  net_profit   REAL,
  target       INT  DEFAULT 2000000,
  risk_level   TEXT,
  risks        TEXT[],
  generated_at TIMESTAMPTZ,
  UNIQUE(channel_id, month)
);

-- ── 6. 지속성 분석 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sustainability (
  id                        SERIAL PRIMARY KEY,
  channel_id                TEXT REFERENCES channels(id),
  quarter                   TEXT,
  topics_produced           INT,
  topics_remaining_estimate INT,
  depletion_risk            TEXT,
  generated_at              TIMESTAMPTZ,
  UNIQUE(channel_id, quarter)
);

-- ── 7. 학습 피드백 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS learning_feedback (
  id                   SERIAL PRIMARY KEY,
  run_id               TEXT REFERENCES pipeline_runs(id),
  channel_id           TEXT REFERENCES channels(id),
  ctr                  REAL,
  avp                  REAL,
  views                INT,
  algorithm_stage      TEXT,
  preferred_title_mode TEXT,
  revenue_on_track     BOOLEAN,
  recorded_at          TIMESTAMPTZ,
  UNIQUE(run_id)
);

-- ── 8. API 쿼터/비용 ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quota_daily (
  id               SERIAL PRIMARY KEY,
  date             DATE,
  service          TEXT,
  total_requests   INT  DEFAULT 0,
  images_generated INT  DEFAULT 0,
  cache_hit_rate   REAL DEFAULT 0,
  quota_used       INT  DEFAULT 0,
  quota_remaining  INT  DEFAULT 0,
  cost_krw         REAL DEFAULT 0,
  UNIQUE(date, service)
);

-- ── 9. 트렌드 주제 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trend_topics (
  id                   SERIAL PRIMARY KEY,
  channel_id           TEXT REFERENCES channels(id),
  original_topic       TEXT,
  reinterpreted_title  TEXT,
  score                REAL,
  grade                TEXT DEFAULT 'review',
  is_trending          BOOLEAN DEFAULT FALSE,
  topic_type           TEXT,
  collected_at         TIMESTAMPTZ,
  UNIQUE(channel_id, reinterpreted_title)
);

-- ── Realtime 활성화 (파이프라인 완료 시 웹 자동 갱신) ───────────
ALTER PUBLICATION supabase_realtime ADD TABLE pipeline_runs;
ALTER PUBLICATION supabase_realtime ADD TABLE kpi_48h;
ALTER PUBLICATION supabase_realtime ADD TABLE revenue_monthly;

-- ── RLS (Row Level Security) ────────────────────────────────────
-- anon key는 클라이언트에 노출되므로 SELECT만 허용.
-- INSERT/UPDATE/DELETE는 service_role key(백엔드 sync 스크립트)로만 가능.

ALTER TABLE channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_48h ENABLE ROW LEVEL SECURITY;
ALTER TABLE revenue_monthly ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_monthly ENABLE ROW LEVEL SECURITY;
ALTER TABLE sustainability ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE quota_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE trend_topics ENABLE ROW LEVEL SECURITY;

-- anon: 읽기 전용
CREATE POLICY "anon_select_channels" ON channels FOR SELECT TO anon USING (true);
CREATE POLICY "anon_select_pipeline_runs" ON pipeline_runs FOR SELECT TO anon USING (true);
CREATE POLICY "anon_select_kpi_48h" ON kpi_48h FOR SELECT TO anon USING (true);
CREATE POLICY "anon_select_revenue_monthly" ON revenue_monthly FOR SELECT TO anon USING (true);
CREATE POLICY "anon_select_risk_monthly" ON risk_monthly FOR SELECT TO anon USING (true);
CREATE POLICY "anon_select_sustainability" ON sustainability FOR SELECT TO anon USING (true);
CREATE POLICY "anon_select_learning_feedback" ON learning_feedback FOR SELECT TO anon USING (true);
CREATE POLICY "anon_select_quota_daily" ON quota_daily FOR SELECT TO anon USING (true);
CREATE POLICY "anon_select_trend_topics" ON trend_topics FOR SELECT TO anon USING (true);

-- service_role: 전체 접근 (RLS를 우회하므로 별도 정책 불필요)
