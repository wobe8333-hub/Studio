// Supabase 데이터베이스 타입 정의

export type Json = string | number | boolean | null | { [key: string]: Json } | Json[]

export interface Database {
  public: {
    Tables: {
      channels: {
        Row: {
          id: string
          category: string
          category_ko: string | null
          youtube_channel_id: string | null
          launch_phase: number | null
          status: string | null
          rpm_proxy: number | null
          revenue_target_monthly: number | null
          monthly_longform_target: number | null
          monthly_shorts_target: number | null
          subscriber_count: number | null
          video_count: number | null
          algorithm_trust_level: string | null
          updated_at: string | null
        }
        Insert: Omit<Database['public']['Tables']['channels']['Row'], 'updated_at'>
        Update: Partial<Database['public']['Tables']['channels']['Row']>
      }
      pipeline_runs: {
        Row: {
          id: string
          channel_id: string | null
          run_state: string | null
          topic_title: string | null
          topic_category: string | null
          topic_score: number | null
          is_trending: boolean | null
          created_at: string | null
          completed_at: string | null
        }
        Insert: Omit<Database['public']['Tables']['pipeline_runs']['Row'], never>
        Update: Partial<Database['public']['Tables']['pipeline_runs']['Row']>
      }
      kpi_48h: {
        Row: {
          id: number
          run_id: string | null
          channel_id: string | null
          video_id: string | null
          impressions: number | null
          ctr: number | null
          views: number | null
          avg_view_percentage: number | null
          avg_view_duration_sec: number | null
          algorithm_stage: string | null
          ctr_level: string | null
          collected_at: string | null
        }
        Insert: Omit<Database['public']['Tables']['kpi_48h']['Row'], 'id'>
        Update: Partial<Database['public']['Tables']['kpi_48h']['Row']>
      }
      revenue_monthly: {
        Row: {
          id: number
          channel_id: string | null
          month: string | null
          adsense_krw: number | null
          affiliate_krw: number | null
          operating_cost: number | null
          net_profit: number | null
          target_achieved: boolean | null
          mix_ratio_adsense: number | null
          mix_ratio_affiliate: number | null
          updated_at: string | null
        }
        Insert: Omit<Database['public']['Tables']['revenue_monthly']['Row'], 'id'>
        Update: Partial<Database['public']['Tables']['revenue_monthly']['Row']>
      }
      risk_monthly: {
        Row: {
          id: number
          channel_id: string | null
          month: string | null
          net_profit: number | null
          target: number | null
          risk_level: string | null
          risks: string[] | null
          generated_at: string | null
        }
        Insert: Omit<Database['public']['Tables']['risk_monthly']['Row'], 'id'>
        Update: Partial<Database['public']['Tables']['risk_monthly']['Row']>
      }
      sustainability: {
        Row: {
          id: number
          channel_id: string | null
          quarter: string | null
          topics_produced: number | null
          topics_remaining_estimate: number | null
          depletion_risk: string | null
          generated_at: string | null
        }
        Insert: Omit<Database['public']['Tables']['sustainability']['Row'], 'id'>
        Update: Partial<Database['public']['Tables']['sustainability']['Row']>
      }
      learning_feedback: {
        Row: {
          id: number
          run_id: string | null
          channel_id: string | null
          ctr: number | null
          avp: number | null
          views: number | null
          algorithm_stage: string | null
          preferred_title_mode: string | null
          revenue_on_track: boolean | null
          recorded_at: string | null
        }
        Insert: Omit<Database['public']['Tables']['learning_feedback']['Row'], 'id'>
        Update: Partial<Database['public']['Tables']['learning_feedback']['Row']>
      }
      quota_daily: {
        Row: {
          id: number
          date: string | null
          service: string | null
          total_requests: number | null
          images_generated: number | null
          cache_hit_rate: number | null
          quota_used: number | null
          quota_remaining: number | null
          cost_krw: number | null
        }
        Insert: Omit<Database['public']['Tables']['quota_daily']['Row'], 'id'>
        Update: Partial<Database['public']['Tables']['quota_daily']['Row']>
      }
      trend_topics: {
        Row: {
          id: number
          channel_id: string | null
          original_topic: string | null
          reinterpreted_title: string | null
          score: number | null
          grade: string | null
          is_trending: boolean | null
          topic_type: string | null
          collected_at: string | null
        }
        Insert: Omit<Database['public']['Tables']['trend_topics']['Row'], 'id'>
        Update: Partial<Database['public']['Tables']['trend_topics']['Row']>
      }
    }
  }
}

// 편의 타입 (Database Row 타입 alias)
export type Channel = Database['public']['Tables']['channels']['Row']
export type PipelineRun = Database['public']['Tables']['pipeline_runs']['Row']
export type TrendTopic = Database['public']['Tables']['trend_topics']['Row']

// AUTO-GENERATED by UiUxAgent — DO NOT EDIT BELOW
export interface Channels {
  id: string;
  category: string;
  category_ko: string;
  youtube_channel_id: string;
  launch_phase: number;
  status: string;
  rpm_proxy: number;
  revenue_target_monthly: number;
  monthly_longform_target: number;
  monthly_shorts_target: number;
  subscriber_count: number;
  video_count: number;
  algorithm_trust_level: string;
  updated_at: string;
}

export interface PipelineRuns {
  id: string;
  channel_id: string;
  run_state: string;
  topic_title: string;
  topic_category: string;
  topic_score: number;
  is_trending: boolean;
  created_at: string;
  completed_at: string;
}

export interface Kpi48h {
  id: number;
  run_id: string;
  channel_id: string;
  video_id: string;
  impressions: number;
  ctr: number;
  views: number;
  avg_view_percentage: number;
  avg_view_duration_sec: number;
  algorithm_stage: string;
  ctr_level: string;
  collected_at: string;
}

export interface RevenueMonthly {
  id: number;
  channel_id: string;
  month: string;
  adsense_krw: number;
  affiliate_krw: number;
  operating_cost: number;
  net_profit: number;
  target_achieved: boolean;
  mix_ratio_adsense: number;
  mix_ratio_affiliate: number;
  updated_at: string;
}

export interface RiskMonthly {
  id: number;
  channel_id: string;
  month: string;
  net_profit: number;
  target: number;
  risk_level: string;
  risks: string[];
  generated_at: string;
}

export interface Sustainability {
  id: number;
  channel_id: string;
  quarter: string;
  topics_produced: number;
  topics_remaining_estimate: number;
  depletion_risk: string;
  generated_at: string;
}

export interface LearningFeedback {
  id: number;
  run_id: string;
  channel_id: string;
  ctr: number;
  avp: number;
  views: number;
  algorithm_stage: string;
  preferred_title_mode: string;
  revenue_on_track: boolean;
  recorded_at: string;
}

export interface QuotaDaily {
  id: number;
  date: string;
  service: string;
  total_requests: number;
  images_generated: number;
  cache_hit_rate: number;
  quota_used: number;
  quota_remaining: number;
  cost_krw: number;
}

export interface TrendTopics {
  id: number;
  channel_id: string;
  original_topic: string;
  reinterpreted_title: string;
  score: number;
  breakdown: Record<string, unknown>;
  grade: string;
  is_trending: boolean;
  topic_type: string;
  collected_at: string;
}
