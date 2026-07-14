"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Activity, Bell, Boxes, ChartNoAxesCombined, Command, FileStack, Gauge, Menu, PanelLeftClose, ScanSearch, Search, Settings2, Sparkles, X } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, cn } from "./ui";

const navigation = [
  { href: "/", label: "Overview", icon: Gauge },
  { href: "/studio", label: "Generation Studio", icon: Sparkles },
  { href: "/gallery", label: "Results Gallery", icon: FileStack },
  { href: "/benchmarks", label: "Benchmarks", icon: ChartNoAxesCombined },
  { href: "/ocr", label: "OCR Eval", icon: ScanSearch },
];

function SynthMark() {
  return (
    <div className="brand-mark" aria-hidden="true">
      <span />
      <span />
      <span />
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let alive = true;
    api.health().then(() => alive && setBackendOnline(true)).catch(() => alive && setBackendOnline(false));
    return () => { alive = false; };
  }, []);

  const current = navigation.find((item) => item.href === pathname)?.label ?? "Workspace";

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      {menuOpen ? <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMenuOpen(false)} /> : null}
      <aside className={cn("sidebar", menuOpen && "sidebar-open")} aria-label="Primary navigation">
        <div className="brand-row">
          <SynthMark />
          <div>
            <strong>NV-SynthForge</strong>
            <span>Document foundry</span>
          </div>
          <button className="icon-button mobile-only" onClick={() => setMenuOpen(false)} aria-label="Close navigation"><X aria-hidden="true" /></button>
        </div>
        <div className="workspace-chip">
          <div className="workspace-icon"><Boxes aria-hidden="true" /></div>
          <div><span>Workspace</span><strong>Production Lab</strong></div>
          <PanelLeftClose aria-hidden="true" />
        </div>
        <nav className="nav-list">
          <p>CONTROL PLANE</p>
          {navigation.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} onClick={() => setMenuOpen(false)} className={cn("nav-item", active && "nav-active")} aria-current={active ? "page" : undefined}>
                <Icon aria-hidden="true" /><span>{item.label}</span>{active ? <i aria-hidden="true" /> : null}
              </Link>
            );
          })}
          <p className="nav-group-label">SYSTEM</p>
          <button className="nav-item" type="button"><Activity aria-hidden="true" /><span>API telemetry</span></button>
          <button className="nav-item" type="button"><Settings2 aria-hidden="true" /><span>Settings</span></button>
        </nav>
        <div className="sidebar-footer">
          <div className="capacity-row"><span>Monthly capacity</span><strong>68%</strong></div>
          <div className="capacity-track"><span /></div>
          <p>68.4K / 100K documents</p>
          <div className="environment-row">
            <span className={cn("status-dot", backendOnline === true && "status-live", backendOnline === false && "status-demo")} />
            <div><strong>{backendOnline === true ? "API connected" : backendOnline === false ? "Demo mode" : "Connecting"}</strong><span>{api.baseUrl}</span></div>
          </div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="topbar-title">
            <button className="icon-button mobile-menu" onClick={() => setMenuOpen(true)} aria-label="Open navigation"><Menu aria-hidden="true" /></button>
            <div><span>NV / WORKSPACE</span><strong>{current}</strong></div>
          </div>
          <label className="global-search">
            <Search aria-hidden="true" />
            <span className="sr-only">Search documents</span>
            <input placeholder="Search documents..." />
            <kbd><Command aria-hidden="true" /> K</kbd>
          </label>
          <div className="top-actions">
            {backendOnline === false ? <Badge tone="warning">DEMO MODE</Badge> : backendOnline === true ? <Badge tone="accent">LIVE API</Badge> : null}
            <button className="icon-button notification" aria-label="Notifications"><Bell aria-hidden="true" /><span /></button>
            <div className="avatar" aria-label="Signed in as Yash">YK</div>
          </div>
        </header>
        <main id="main-content" className="content" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}
