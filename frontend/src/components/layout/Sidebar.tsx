import { LayoutDashboard, Cpu, FolderOpen, X } from 'lucide-react'

interface NavItem {
  label: string
  icon: React.ReactNode
  active?: boolean
}

const navItems: NavItem[] = [
  { label: 'Dashboard', icon: <LayoutDashboard size={18} />, active: true },
  { label: 'Models',    icon: <Cpu size={18} /> },
  { label: 'Projects',  icon: <FolderOpen size={18} /> },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/20 md:hidden"
          style={{ backdropFilter: 'blur(2px)' }}
          onClick={onClose}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`
          fixed top-0 left-0 z-50 h-full w-56 flex flex-col pt-4 pb-6 px-3 transition-transform duration-300
          md:static md:translate-x-0 md:z-auto
          ${open ? 'translate-x-0' : '-translate-x-full'}
        `}
        style={{
          background: 'rgba(255,255,255,0.14)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          borderRight: '1px solid rgba(255,255,255,0.22)',
          boxShadow: '4px 0 24px rgba(0,0,0,0.08)',
        }}
      >
        {/* Mobile close */}
        <button
          className="md:hidden self-end mb-4 p-1 rounded-lg text-[#7a8fb5] hover:text-[#1a2942] transition-colors"
          onClick={onClose}
          aria-label="Close sidebar"
        >
          <X size={18} />
        </button>

        {/* Logo area */}
        <div className="flex items-center gap-2.5 px-2 mb-8 mt-2">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center text-white text-xs font-bold shrink-0"
            style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}
          >
            AI
          </div>
          <span className="font-bold text-[#1a2942] text-sm">Usage</span>
        </div>

        {/* Nav items */}
        <nav className="flex flex-col gap-1">
          {navItems.map(item => (
            <button
              key={item.label}
              className={`
                flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium text-left transition-all
                ${item.active
                  ? 'bg-[#6366f1] text-white shadow-sm'
                  : 'text-[#4a5f7f] hover:bg-white/30 hover:text-[#1a2942]'}
              `}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>

        {/* Bottom: version */}
        <div className="mt-auto px-2">
          <span className="text-[10px] text-[#7a8fb5] uppercase tracking-wide">v0.3.0</span>
        </div>
      </aside>
    </>
  )
}
