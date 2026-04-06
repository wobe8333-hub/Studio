'use client'

import { motion } from 'motion/react'

// ─── StaggerContainer ────────────────────────────────────────────────────────
// 자식 컴포넌트를 순차적으로 등장시키는 컨테이너
interface ContainerProps {
  children: React.ReactNode
  className?: string
}

export function StaggerContainer({ children, className }: ContainerProps) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: {
          transition: { staggerChildren: 0.08 },
        },
      }}
    >
      {children}
    </motion.div>
  )
}

// ─── StaggerItem ─────────────────────────────────────────────────────────────
// StaggerContainer 안에서 순차 등장하는 아이템
export function StaggerItem({ children, className }: ContainerProps) {
  return (
    <motion.div
      className={className}
      variants={{
        hidden: { opacity: 0, y: 16 },
        visible: {
          opacity: 1,
          y: 0,
          transition: { type: 'spring', stiffness: 260, damping: 20 },
        },
      }}
    >
      {children}
    </motion.div>
  )
}

// ─── ScrollReveal ─────────────────────────────────────────────────────────────
// 스크롤하면서 뷰포트에 진입할 때 등장하는 섹션
export function ScrollReveal({ children, className }: ContainerProps) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}

// ─── AnimatedCard ─────────────────────────────────────────────────────────────
// 뷰포트 진입 페이드인 + 호버 시 살짝 위로 이동 (채널 카드용)
interface AnimatedCardProps {
  children: React.ReactNode
  className?: string
  delay?: number
}

export function AnimatedCard({ children, className, delay = 0 }: AnimatedCardProps) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 260, damping: 20, delay }}
      whileHover={{ y: -3, transition: { duration: 0.18 } }}
    >
      {children}
    </motion.div>
  )
}

