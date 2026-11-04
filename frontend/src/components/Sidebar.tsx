import React from 'react';
import {
  LayoutDashboard,
  Briefcase,
  Radio,
  ShieldAlert,
  ListOrdered,
  Terminal,
  Settings,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { SidebarSection } from '../types';

interface SidebarProps {
  activeSection: SidebarSection;
  onSelectSection: (section: SidebarSection) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  counts: {
    positions: number;
    signals: number;
    orders: number;
    audit: number;
    emergencyStop: boolean;
  };
}

interface NavItem {
  id: SidebarSection;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number | string;
  badgeAlert?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeSection,
  onSelectSection,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
  counts,
}) => {
  const navItems: NavItem[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      description: 'Vista principal con gráfico TradingView',
      icon: LayoutDashboard,
    },
    {
      id: 'positions',
      label: 'Posiciones',
      description: 'Posiciones abiertas, PnL, historial',
      icon: Briefcase,
      badge: counts.positions,
    },
    {
      id: 'signals',
      label: 'Señales',
      description: 'Señales recientes BUY/SELL/NO_OP',
      icon: Radio,
      badge: counts.signals,
    },
    {
      id: 'risk',
      label: 'Riesgo',
      description: 'Límites actuales, decisiones, emergency stop',
      icon: ShieldAlert,
      badge: counts.emergencyStop ? 'STOP' : undefined,
      badgeAlert: counts.emergencyStop,
    },
    {
      id: 'orders',
      label: 'Órdenes',
      description: 'Historial de órdenes, fills, rechazos',
      icon: ListOrdered,
      badge: counts.orders,
    },
    {
      id: 'audit',
      label: 'Audit Log',
      description: 'Eventos en tiempo real (Hash Chain)',
      icon: Terminal,
      badge: counts.audit,
    },
    {
      id: 'config',
      label: 'Configuración',
      description: 'Instrumentos, estrategia, límites y Binance',
      icon: Settings,
    },
  ];

  const handleSelect = (id: SidebarSection) => {
    onSelectSection(id);
    onCloseMobile();
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {mobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden transition-opacity duration-300"
        />
      )}

      {/* Sidebar Container: Fixed left on desktop, Drawer overlay on mobile */}
      <aside
        className={`fixed top-0 left-0 z-50 h-screen bg-[#0b101b] border-r border-slate-800 flex flex-col transition-all duration-300 ease-in-out select-none ${
          collapsed ? 'lg:w-16' : 'lg:w-64'
        } ${
          mobileOpen
            ? 'translate-x-0 w-64 shadow-2xl'
            : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Top Brand + Hamburger Toggle */}
        <div className="h-16 px-3 border-b border-slate-800 flex items-center justify-between gap-2 shrink-0">
          {!collapsed && (
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-lg bg-sky-500/15 border border-sky-500/40 flex items-center justify-center text-sky-400 font-mono font-bold text-sm shrink-0">
                TA
              </div>
              <div className="truncate">
                <div className="text-xs font-bold font-mono text-white tracking-tight truncate">
                  TRADING AGENT
                </div>
                <div className="text-[10px] font-mono text-amber-400 truncate">
                  SIMULACIÓN / PAPER
                </div>
              </div>
            </div>
          )}

          {/* Desktop Hamburger / Collapse Button */}
          <button
            type="button"
            onClick={onToggleCollapse}
            title={collapsed ? 'Expandir menú lateral' : 'Colapsar menú lateral'}
            aria-label="Alternar barra lateral"
            className={`hidden lg:flex items-center justify-center p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 transition cursor-pointer ${
              collapsed ? 'mx-auto' : ''
            }`}
          >
            <Menu className="w-4 h-4" />
          </button>

          {/* Mobile Close Drawer Button */}
          <button
            type="button"
            onClick={onCloseMobile}
            aria-label="Cerrar menú móvil"
            className="lg:hidden p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => handleSelect(item.id)}
                title={collapsed ? `${item.label} — ${item.description}` : item.description}
                className={`group relative w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-mono text-xs transition-all duration-200 cursor-pointer ${
                  isActive
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 font-bold shadow-sm'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/80 border border-transparent'
                } ${collapsed ? 'lg:justify-center lg:px-0' : ''}`}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 transition-colors ${
                    isActive ? 'text-sky-400' : 'text-slate-400 group-hover:text-slate-200'
                  }`}
                />

                {/* Label & Badge when expanded (or on mobile drawer) */}
                <span
                  className={`truncate transition-opacity duration-200 ${
                    collapsed ? 'lg:hidden' : 'block'
                  }`}
                >
                  {item.label}
                </span>

                {item.badge !== undefined && (
                  <span
                    className={`ml-auto px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                      collapsed ? 'lg:hidden' : 'inline-block'
                    } ${
                      item.badgeAlert
                        ? 'bg-rose-500/25 text-rose-300 border border-rose-500/40 animate-pulse'
                        : isActive
                        ? 'bg-sky-500/30 text-sky-200'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom Collapse / Expand Footer */}
        <div className="p-2.5 border-t border-slate-800 shrink-0">
          <button
            type="button"
            onClick={onToggleCollapse}
            className="hidden lg:flex w-full items-center justify-center gap-2 py-2 px-2.5 rounded-lg bg-slate-900/70 hover:bg-slate-800 text-slate-400 hover:text-slate-200 text-[11px] font-mono border border-slate-800/80 transition cursor-pointer"
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4 text-sky-400" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4 text-sky-400" />
                <span>Colapsar Sidebar</span>
              </>
            )}
          </button>
        </div>
      </aside>
    </>
  );
};
