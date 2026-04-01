import { type ButtonHTMLAttributes, type ReactNode } from 'react'

type Variant = 'neo' | 'glass' | 'ghost' | 'accent'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  children: ReactNode
}

const sizeClasses: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-5 py-2.5 text-sm',
  lg: 'px-7 py-3 text-base',
}

const variantClasses: Record<Variant, string> = {
  neo:    'btn-neo',
  glass:  'btn-glass',
  ghost:  'bg-transparent border border-[#a8b9d1] text-[#4a5f7f] rounded-full hover:bg-[#e8edf5] cursor-pointer transition-colors',
  accent: 'bg-[#6366f1] text-white rounded-full font-semibold cursor-pointer hover:bg-[#4f46e5] transition-colors shadow-sm',
}

export function Button({ variant = 'neo', size = 'md', children, className = '', ...props }: ButtonProps) {
  return (
    <button
      className={`${variantClasses[variant]} ${sizeClasses[size]} font-semibold ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
