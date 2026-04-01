import { type ReactNode } from 'react'

type Variant = 'neo' | 'neo-sm' | 'glass'

interface CardProps {
  variant?: Variant
  className?: string
  children: ReactNode
}

const variantClasses: Record<Variant, string> = {
  'neo':    'card-neo',
  'neo-sm': 'card-neo-sm',
  'glass':  'card-glass',
}

export function Card({ variant = 'neo', className = '', children }: CardProps) {
  return (
    <div className={`${variantClasses[variant]} ${className}`}>
      {children}
    </div>
  )
}
