import { Menu, SlidersHorizontal } from 'lucide-react'
import { Button } from '../ui/Button'

interface HeaderProps {
  onMenuToggle: () => void
  onFilterToggle: () => void
}

export function Header({ onMenuToggle, onFilterToggle }: HeaderProps) {
  return (
    <header
      className="sticky top-0 z-30 h-14 flex items-center justify-between px-4 md:px-6"
      style={{
        background: 'rgba(240,244,248,0.75)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(168,185,209,0.3)',
        boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
      }}
    >
      <div className="flex items-center gap-3">
        <button
          className="md:hidden p-1.5 rounded-lg text-[#4a5f7f] hover:bg-[#e8edf5] transition-colors"
          onClick={onMenuToggle}
          aria-label="Toggle sidebar"
        >
          <Menu size={20} />
        </button>
        <div className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold"
            style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}
          >
            AI
          </div>
          <span className="font-semibold text-[#1a2942] text-sm">Usage Dashboard</span>
        </div>
      </div>

      <Button variant="ghost" size="sm" onClick={onFilterToggle} className="flex items-center gap-1.5">
        <SlidersHorizontal size={14} />
        Filters
      </Button>
    </header>
  )
}
