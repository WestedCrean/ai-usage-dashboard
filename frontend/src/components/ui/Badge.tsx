import { type ReactNode } from 'react'

type Color = 'indigo' | 'purple' | 'emerald' | 'amber' | 'rose' | 'gray'

interface BadgeProps {
  color?: Color
  children: ReactNode
  className?: string
}

const colorClasses: Record<Color, string> = {
  indigo:  'bg-indigo-100 text-indigo-700',
  purple:  'bg-purple-100 text-purple-700',
  emerald: 'bg-emerald-100 text-emerald-700',
  amber:   'bg-amber-100 text-amber-700',
  rose:    'bg-rose-100 text-rose-700',
  gray:    'bg-gray-100 text-gray-600',
}

export function Badge({ color = 'indigo', children, className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${colorClasses[color]} ${className}`}>
      {children}
    </span>
  )
}
