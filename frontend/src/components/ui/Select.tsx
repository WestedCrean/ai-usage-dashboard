import { type SelectHTMLAttributes } from 'react'

interface SelectOption {
  value: string
  label: string
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  options: SelectOption[]
  glass?: boolean
}

export function Select({ label, options, glass = false, className = '', ...props }: SelectProps) {
  const baseClass = glass ? 'input-glass' : 'input-neo'

  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className={`text-xs font-semibold uppercase tracking-wide ${glass ? 'text-white/70' : 'text-[#7a8fb5]'}`}>
          {label}
        </label>
      )}
      <select
        className={`${baseClass} w-full px-4 py-2.5 text-sm cursor-pointer ${className}`}
        {...props}
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}
