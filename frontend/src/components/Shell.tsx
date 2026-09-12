"use client";

/**
 * The signed-in chrome: sidebar, top bar and content column.
 *
 * The sidebar has three states, and one button drives whichever applies:
 *
 *   mobile  (<lg)  off-canvas drawer over a backdrop
 *   desktop expanded   240px, icons + labels + section headings
 *   desktop collapsed  64px icon rail, labels on hover
 *
 * The desktop choice is remembered in localStorage — a sidebar that re-opens on
 * every navigation is not a preference, it is a nuisance. The mobile drawer is
 * deliberately *not* remembered: it covers the content, so it should always
 * open closed.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { initials } from "@/lib/format";
import type { AIStatus, Role } from "@/lib/types";
import {
  ApplicationsIcon,
  CandidatesIcon,
  ChevronDownIcon,
  CloseIcon,
  CollapseIcon,
  DashboardIcon,
  ExpandIcon,
  JobsIcon,
  LogoutIcon,
  MenuIcon,
  ProfileIcon,
  ResumeIcon,
  ScreeningIcon,
  type Icon,
} from "./icons";
import { Badge, cx } from "./ui";

const COLLAPSED_KEY = "air.sidebar.collapsed";

interface NavItem {
  href: string;
  label: string;
  icon: Icon;
  /** Shows the pending-review count. Only the recruiter's screening queue uses it. */
  badge?: "pendingReviews";
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

// Grouped rather than one flat list: five items with no structure make the user
// read all five every time. The headings hide in the collapsed rail, where a
// separator carries the same grouping without the words.
const CANDIDATE_NAV: NavGroup[] = [
  {
    label: "Overview",
    items: [{ href: "/candidate/dashboard", label: "Dashboard", icon: DashboardIcon }],
  },
  {
    label: "My details",
    items: [
      { href: "/candidate/profile", label: "Profile", icon: ProfileIcon },
      { href: "/candidate/resume", label: "Resume", icon: ResumeIcon },
    ],
  },
  {
    label: "Opportunities",
    items: [
      { href: "/candidate/jobs", label: "Jobs", icon: JobsIcon },
      { href: "/candidate/applications", label: "Applications", icon: ApplicationsIcon },
    ],
  },
];

const RECRUITER_NAV: NavGroup[] = [
  {
    label: "Overview",
    items: [{ href: "/recruiter/dashboard", label: "Dashboard", icon: DashboardIcon }],
  },
  {
    label: "Hiring",
    items: [
      { href: "/recruiter/jobs", label: "Jobs", icon: JobsIcon },
      { href: "/recruiter/candidates", label: "Candidates", icon: CandidatesIcon },
      { href: "/recruiter/applications", label: "Applications", icon: ApplicationsIcon },
    ],
  },
  {
    label: "AI",
    items: [
      {
        href: "/recruiter/screening",
        label: "AI Screening",
        icon: ScreeningIcon,
        badge: "pendingReviews",
      },
    ],
  },
];

export function Shell({ role, children }: { role: Role; children: ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  // Gates the width transition so the stored state does not visibly slide in
  // on first paint.
  const [ready, setReady] = useState(false);

  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [pendingReviews, setPendingReviews] = useState(0);

  const groups = role === "RECRUITER" ? RECRUITER_NAV : CANDIDATE_NAV;
  const activeItem = groups
    .flatMap((group) => group.items)
    .find((item) => pathname?.startsWith(item.href));

  // Restore the remembered desktop width. localStorage cannot be read during
  // render without a hydration mismatch, so it happens here instead.
  useEffect(() => {
    try {
      setCollapsed(window.localStorage.getItem(COLLAPSED_KEY) === "1");
    } catch {
      /* private mode or blocked storage — the default is fine */
    }
    setReady(true);
  }, []);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(COLLAPSED_KEY, next ? "1" : "0");
      } catch {
        /* not remembering it is survivable; failing to toggle is not */
      }
      return next;
    });
  }, []);

  useEffect(() => {
    api.aiStatus().then(setAiStatus).catch(() => setAiStatus(null));
  }, []);

  // Refreshed per navigation so the badge reflects decisions just made.
  useEffect(() => {
    if (role !== "RECRUITER") return;
    api
      .recruiterMetrics()
      .then((metrics) => setPendingReviews(metrics.pending_hitl_reviews))
      .catch(() => setPendingReviews(0));
  }, [role, pathname]);

  // Navigating closes the drawer — otherwise it stays over the page you asked for.
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  // While the drawer is open: Escape closes it, the page behind must not
  // scroll, and widening past `lg` drops it — the sidebar is permanent there,
  // so a still-"open" drawer would leave the scroll lock behind.
  useEffect(() => {
    if (!drawerOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawerOpen(false);
    };
    const desktop = window.matchMedia("(min-width: 1024px)");
    const onBreakpointChange = () => {
      if (desktop.matches) setDrawerOpen(false);
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    desktop.addEventListener("change", onBreakpointChange);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
      desktop.removeEventListener("change", onBreakpointChange);
    };
  }, [drawerOpen]);

  const badgeCounts = { pendingReviews };

  return (
    // `lg:flex` is what puts the sidebar beside the content: below it the aside
    // is `fixed` and out of flow, above it it becomes a static flex child.
    <div className="min-h-screen bg-slate-50 lg:flex">
      {/* Backdrop — mobile only, and only while the drawer is open. */}
      <div
        onClick={() => setDrawerOpen(false)}
        aria-hidden="true"
        className={cx(
          "fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-[1px] transition-opacity lg:hidden",
          drawerOpen ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />

      <aside
        aria-label="Main navigation"
        className={cx(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-200 bg-white",
          "lg:static lg:h-screen lg:translate-x-0",
          ready && "transition-[transform,width] duration-200 ease-out",
          drawerOpen ? "translate-x-0 shadow-xl" : "-translate-x-full",
          collapsed ? "lg:w-16" : "lg:w-60",
        )}
      >
        <SidebarHeader
          role={role}
          collapsed={collapsed}
          onCloseDrawer={() => setDrawerOpen(false)}
        />

        <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-3">
          {groups.map((group) => (
            <div key={group.label}>
              {collapsed ? (
                <div className="mx-auto mb-2 h-px w-6 bg-slate-200 lg:block" />
              ) : (
                <p className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  {group.label}
                </p>
              )}
              <div className="space-y-0.5">
                {group.items.map((item) => (
                  <NavLink
                    key={item.href}
                    item={item}
                    active={pathname?.startsWith(item.href) ?? false}
                    collapsed={collapsed}
                    count={item.badge ? badgeCounts[item.badge] : 0}
                  />
                ))}
              </div>
            </div>
          ))}
        </nav>

        <AiStatusPanel status={aiStatus} collapsed={collapsed} />
      </aside>

      {/* `min-w-0` lets wide content shrink instead of pushing the layout out. */}
      <div className="flex min-h-screen min-w-0 flex-1 flex-col lg:h-screen lg:overflow-hidden">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-2.5 backdrop-blur sm:px-6 lg:static">
          {/* One toggle, two meanings: drawer on mobile, rail on desktop. */}
          <button
            onClick={() => setDrawerOpen(true)}
            aria-label="Open navigation"
            aria-expanded={drawerOpen}
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
          >
            <MenuIcon />
          </button>
          <button
            onClick={toggleCollapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="hidden rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:block"
          >
            {collapsed ? <ExpandIcon /> : <CollapseIcon />}
          </button>

          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-slate-900">
              {activeItem?.label ?? "AI Recruitment"}
            </p>
            <p className="truncate text-[11px] text-slate-500">
              {role === "RECRUITER" ? "Recruiter portal" : "Candidate portal"}
            </p>
          </div>

          <UserMenu
            name={user?.full_name ?? ""}
            email={user?.email ?? ""}
            role={role}
            onLogout={logout}
          />
        </header>

        <main className="flex-1 overflow-y-auto px-4 py-5 sm:px-6 sm:py-6">
          <div className="mx-auto w-full max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  );
}

function SidebarHeader({
  role,
  collapsed,
  onCloseDrawer,
}: {
  role: Role;
  collapsed: boolean;
  onCloseDrawer: () => void;
}) {
  return (
    <div
      className={cx(
        "flex items-center gap-2.5 border-b border-slate-100 py-4",
        collapsed ? "lg:justify-center lg:px-0" : "",
        "px-4",
      )}
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-[11px] font-bold text-white">
        AI
      </div>
      <div className={cx("min-w-0 leading-tight", collapsed && "lg:hidden")}>
        <p className="truncate text-sm font-semibold text-slate-900">Recruitment</p>
        <p className="truncate text-[11px] text-slate-500">
          {role === "RECRUITER" ? "Recruiter" : "Candidate"}
        </p>
      </div>
      {/* Drawer close. The desktop toggle lives in the top bar. */}
      <button
        onClick={onCloseDrawer}
        aria-label="Close navigation"
        className="ml-auto rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
      >
        <CloseIcon />
      </button>
    </div>
  );
}

function NavLink({
  item,
  active,
  collapsed,
  count,
}: {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
  count: number;
}) {
  const IconComponent = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      title={collapsed ? item.label : undefined}
      className={cx(
        "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
        collapsed && "lg:justify-center lg:px-0",
        active
          ? "bg-slate-900 font-medium text-white"
          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
      )}
    >
      <span className="relative shrink-0">
        <IconComponent className="h-5 w-5" />
        {/* Collapsed, there is no room for a count — a dot still says "look here". */}
        {collapsed && count > 0 ? (
          <span className="absolute -right-1 -top-1 hidden h-2 w-2 rounded-full bg-amber-500 ring-2 ring-white lg:block" />
        ) : null}
      </span>

      <span className={cx("flex-1 truncate", collapsed && "lg:hidden")}>{item.label}</span>

      {count > 0 ? (
        <span
          className={cx(
            "rounded-full px-1.5 py-0.5 text-[10px] font-semibold tabular-nums",
            collapsed && "lg:hidden",
            active ? "bg-white/20 text-white" : "bg-amber-100 text-amber-700",
          )}
        >
          {count}
        </span>
      ) : null}

      {/* Hover label for the collapsed rail, where the text is hidden. */}
      {collapsed ? (
        <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 hidden -translate-y-1/2 whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 lg:block">
          {item.label}
          {count > 0 ? ` · ${count} pending` : ""}
        </span>
      ) : null}
    </Link>
  );
}

/**
 * Which model is live, in the sidebar footer.
 *
 * It stays visible because the difference between real model output and the
 * rule-based fallback is the single most important thing to know while reading
 * a match score.
 */
function AiStatusPanel({
  status,
  collapsed,
}: {
  status: AIStatus | null;
  collapsed: boolean;
}) {
  const tone = !status ? "bg-slate-300" : status.using_fallback ? "bg-amber-500" : "bg-emerald-500";

  if (collapsed) {
    return (
      <div
        className="hidden justify-center border-t border-slate-100 py-3 lg:flex"
        title={status ? `AI: ${status.llm}` : "Checking the AI layer"}
      >
        <span className={cx("h-2.5 w-2.5 rounded-full", tone)} />
      </div>
    );
  }

  return (
    <div className={cx("border-t border-slate-100 px-4 py-3", collapsed && "lg:hidden")}>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
        AI layer
      </p>
      {status ? (
        <div className="mt-1.5 space-y-1">
          <Badge tone={status.using_fallback ? "amber" : "green"}>
            {status.using_fallback ? "Rule-based fallback" : "LLM active"}
          </Badge>
          <p className="truncate text-[11px] text-slate-500" title={status.llm}>
            {status.llm}
          </p>
          <p className="truncate text-[11px] text-slate-400" title={status.embeddings}>
            {status.embeddings}
          </p>
        </div>
      ) : (
        <p className="mt-1.5 text-[11px] text-slate-400">Checking…</p>
      )}
    </div>
  );
}

function UserMenu({
  name,
  email,
  role,
  onLogout,
}: {
  name: string;
  email: string;
  role: Role;
  onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // A dropdown that ignores an outside click feels broken, so close on both a
  // click elsewhere and Escape.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative shrink-0">
      <button
        onClick={() => setOpen(!open)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-lg py-1.5 pl-1.5 pr-2 text-left hover:bg-slate-100"
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-700">
          {initials(name)}
        </span>
        {/* The name is dropped on narrow screens; the avatar still identifies it. */}
        <span className="hidden min-w-0 leading-tight sm:block">
          <span className="block truncate text-sm font-medium text-slate-900">{name}</span>
          <span className="block truncate text-[11px] text-slate-500">
            {role === "RECRUITER" ? "Recruiter" : "Candidate"}
          </span>
        </span>
        <ChevronDownIcon
          className={cx("h-4 w-4 shrink-0 text-slate-400 transition-transform", open && "rotate-180")}
        />
      </button>

      {open ? (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-1.5 w-60 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg"
        >
          <div className="border-b border-slate-100 px-3.5 py-3">
            <p className="truncate text-sm font-medium text-slate-900">{name}</p>
            <p className="truncate text-xs text-slate-500">{email}</p>
            <span className="mt-1.5 inline-block">
              <Badge tone={role === "RECRUITER" ? "blue" : "slate"}>
                {role === "RECRUITER" ? "Recruiter" : "Candidate"}
              </Badge>
            </span>
          </div>
          <button
            role="menuitem"
            onClick={onLogout}
            className="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50"
          >
            <LogoutIcon className="h-4 w-4 text-slate-400" />
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}
