'use server'

import { revalidatePath } from 'next/cache'
import { readKasJson, writeKasJson, QaResult, VariantManifest } from '@/lib/fs-helpers'

/**
 * Step11 QA 결과의 human_review.completed를 true로 업데이트
 */
export async function approveHumanReview(
  channelId: string,
  runId: string,
  reviewer: string = 'dashboard',
): Promise<{ ok: boolean; error?: string }> {
  const relPath = `runs/${channelId}/${runId}/step11/qa_result.json`
  const qa = await readKasJson<QaResult>(relPath)
  if (!qa) return { ok: false, error: 'qa_result.json 파일 없음' }

  const updated: QaResult = {
    ...qa,
    human_review: {
      ...qa.human_review,
      completed: true,
      reviewer,
    },
  }
  await writeKasJson(relPath, updated)
  revalidatePath('/qa')
  return { ok: true }
}

/**
 * Step10 배리언트 선택: variant_manifest.json의 selected_title_ref 업데이트
 * + step08/title.json의 selected 필드도 선택된 제목으로 업데이트
 */
export async function selectTitleVariant(
  channelId: string,
  runId: string,
  titleRef: string,
): Promise<{ ok: boolean; error?: string }> {
  const manifestPath = `runs/${channelId}/${runId}/step08/variants/variant_manifest.json`
  const manifest = await readKasJson<VariantManifest>(manifestPath)
  if (!manifest) return { ok: false, error: 'variant_manifest.json 파일 없음' }

  const selected = manifest.title_variants.find((v) => v.ref === titleRef)
  if (!selected) return { ok: false, error: `ref "${titleRef}" 없음` }

  const updatedManifest: VariantManifest = { ...manifest, selected_title_ref: titleRef }
  await writeKasJson(manifestPath, updatedManifest)

  const titlePath = `runs/${channelId}/${runId}/step08/title.json`
  const titleJson = await readKasJson<{ title_candidates: string[]; selected: string }>(titlePath)
  if (titleJson) {
    await writeKasJson(titlePath, { ...titleJson, selected: selected.title })
  }

  revalidatePath('/qa')
  return { ok: true }
}

/**
 * Step10 배리언트 선택: variant_manifest.json의 selected_thumbnail_ref 업데이트
 */
export async function selectThumbnailVariant(
  channelId: string,
  runId: string,
  thumbnailRef: string,
): Promise<{ ok: boolean; error?: string }> {
  const manifestPath = `runs/${channelId}/${runId}/step08/variants/variant_manifest.json`
  const manifest = await readKasJson<VariantManifest>(manifestPath)
  if (!manifest) return { ok: false, error: 'variant_manifest.json 파일 없음' }

  const updatedManifest: VariantManifest = { ...manifest, selected_thumbnail_ref: thumbnailRef }
  await writeKasJson(manifestPath, updatedManifest)
  revalidatePath('/qa')
  return { ok: true }
}
