import { X } from 'lucide-react'
import { Select } from '../ui/Select'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'

export interface FilterValues {
  model: string
  project: string
  team: string
  from: string
  to: string
}

interface FilterPanelProps {
  open: boolean
  onClose: () => void
  values: FilterValues
  onChange: (values: FilterValues) => void
  modelOptions: Array<{ value: string; label: string }>
  projectOptions: Array<{ value: string; label: string }>
  teamOptions: Array<{ value: string; label: string }>
}

export function FilterPanel({
  open,
  onClose,
  values,
  onChange,
  modelOptions,
  projectOptions,
  teamOptions,
}: FilterPanelProps) {
  const set = (key: keyof FilterValues) => (
    e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>
  ) => onChange({ ...values, [key]: e.target.value })

  const reset = () =>
    onChange({ model: '', project: '', team: '', from: '', to: '' })

  if (!open) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/20"
        style={{ backdropFilter: 'blur(3px)', WebkitBackdropFilter: 'blur(3px)' }}
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className="fixed top-0 right-0 z-50 h-full w-72 flex flex-col px-5 py-6 gap-5"
        style={{
          background: 'linear-gradient(160deg, rgba(99,102,241,0.18) 0%, rgba(139,92,246,0.14) 100%)',
          backdropFilter: 'blur(18px)',
          WebkitBackdropFilter: 'blur(18px)',
          borderLeft: '1px solid rgba(255,255,255,0.2)',
          boxShadow: '-8px 0 40px rgba(0,0,0,0.15)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-white text-base">Filters</h3>
          <button
            className="text-white/60 hover:text-white transition-colors"
            onClick={onClose}
            aria-label="Close filters"
          >
            <X size={18} />
          </button>
        </div>

        {/* Controls */}
        <div className="flex flex-col gap-4 flex-1 overflow-y-auto">
          <Select
            glass
            label="Model"
            options={[{ value: '', label: 'All Models' }, ...modelOptions]}
            value={values.model}
            onChange={set('model')}
          />

          <Select
            glass
            label="Project"
            options={[{ value: '', label: 'All Projects' }, ...projectOptions]}
            value={values.project}
            onChange={set('project')}
          />

          <Select
            glass
            label="Team"
            options={[{ value: '', label: 'All Teams' }, ...teamOptions]}
            value={values.team}
            onChange={set('team')}
          />

          <Input
            glass
            label="From"
            type="date"
            value={values.from}
            onChange={set('from')}
          />

          <Input
            glass
            label="To"
            type="date"
            value={values.to}
            onChange={set('to')}
          />
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2 border-t border-white/15">
          <Button variant="glass" size="sm" className="flex-1" onClick={reset}>
            Reset
          </Button>
          <Button variant="glass" size="sm" className="flex-1 !bg-white/25" onClick={onClose}>
            Apply
          </Button>
        </div>
      </div>
    </>
  )
}
