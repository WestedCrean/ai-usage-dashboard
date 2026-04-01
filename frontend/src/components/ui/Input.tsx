import { type InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  glass?: boolean
}

export function Input({ label, error, glass = false, className = '', ...props }: InputProps) {
  const baseClass = glass ? 'input-glass' : 'input-neo'

  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className={`text-xs font-semibold uppercase tracking-wide ${glass ? 'text-white/70' : 'text-[#7a8fb5]'}`}>
          {label}
        </label>
      )}
      <input
        className={`${baseClass} w-full px-4 py-2.5 text-sm ${className}`}
        {...props}
      />
      {error && (
        <span className="text-xs text-[#ef4444]">{error}</span>
      )}
    </div>
  )
}
