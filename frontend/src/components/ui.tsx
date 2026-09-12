"use client";

/**
 * The shared UI kit: cards, badges, bars, tables, buttons, inputs.
 *
 * Every screen is built from these, so spacing, radius and colour stay
 * consistent without a component library.
 */
import type { ChangeEvent, ReactNode } from "react";

import type { Tone } from "@/lib/format";
import { scoreTone } from "@/lib/format";

export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

const TONE_BADGE: Record<Tone, string> = {
  green: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  amber: "bg-amber-50 text-amber-700 ring-amber-600/20",
  red: "bg-rose-50 text-rose-700 ring-rose-600/20",
  blue: "bg-sky-50 text-sky-700 ring-sky-600/20",
  slate: "bg-slate-100 text-slate-600 ring-slate-500/20",
};

const TONE_BAR: Record<Tone, string> = {
  green: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-rose-500",
  blue: "bg-sky-500",
  slate: "bg-slate-400",
};

const TONE_TEXT: Record<Tone, string> = {
  green: "text-emerald-600",
  amber: "text-amber-600",
  red: "text-rose-600",
  blue: "text-sky-600",
  slate: "text-slate-600",
};

// --- Layout ------------------------------------------------------------------

export function Card({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cx(
        "rounded-xl border border-slate-200 bg-white shadow-sm",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
}) {
  return (
    // Stacks below `sm`: an action with two or three controls would otherwise
    // crush the title down to a couple of characters on a phone.
    <div className="flex flex-col gap-2.5 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <div className="min-w-0">
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
        {subtitle ? (
          <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
        ) : null}
      </div>
      {action ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{action}</div>
      ) : null}
    </div>
  );
}

export function CardBody({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cx("px-5 py-4", className)}>{children}</div>;
}

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3 sm:mb-6">
      <div className="min-w-0">
        <h1 className="text-lg font-semibold text-slate-900 sm:text-xl">{title}</h1>
        {subtitle ? (
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
        ) : null}
      </div>
      {action ? (
        <div className="flex flex-wrap items-center gap-2">{action}</div>
      ) : null}
    </div>
  );
}

// --- Feedback ----------------------------------------------------------------

export function Badge({
  children,
  tone = "slate",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        TONE_BADGE[tone],
      )}
    >
      {children}
    </span>
  );
}

export function Alert({
  tone = "red",
  children,
}: {
  tone?: Tone;
  children: ReactNode;
}) {
  if (!children) return null;
  return (
    <div
      className={cx(
        "rounded-lg px-3 py-2 text-sm ring-1 ring-inset",
        TONE_BADGE[tone],
      )}
      role="status"
    >
      {children}
    </div>
  );
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-5 py-12 text-center">
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {hint ? <p className="max-w-md text-sm text-slate-500">{hint}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 px-5 py-10 text-sm text-slate-500">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
      {label}
    </div>
  );
}

// --- Metrics -----------------------------------------------------------------

export function StatCard({
  label,
  value,
  hint,
  tone = "slate",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: Tone;
}) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className={cx("mt-1.5 text-2xl font-semibold", TONE_TEXT[tone])}>
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </Card>
  );
}

export function ProgressBar({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: Tone;
}) {
  const resolved = tone ?? scoreTone(value);
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-slate-600">{label}</span>
        <span className={cx("font-semibold tabular-nums", TONE_TEXT[resolved])}>
          {Math.round(value)}%
        </span>
      </div>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className={cx("h-full rounded-full transition-all", TONE_BAR[resolved])}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}

/** The big circular overall-match readout on the screening page. */
export function ScoreRing({
  value,
  label = "Overall match",
  size = 132,
}: {
  value: number;
  label?: string;
  size?: number;
}) {
  const tone = scoreTone(value);
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = (Math.max(0, Math.min(100, value)) / 100) * circumference;
  const strokeColor = {
    green: "#10b981",
    blue: "#0ea5e9",
    amber: "#f59e0b",
    red: "#f43f5e",
    slate: "#94a3b8",
  }[tone];

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#e2e8f0"
            strokeWidth={stroke}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${filled} ${circumference}`}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cx("text-3xl font-semibold", TONE_TEXT[tone])}>
            {Math.round(value)}%
          </span>
        </div>
      </div>
      <span className="mt-3 text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </span>
    </div>
  );
}

export function SkillChips({
  items,
  tone = "slate",
  empty = "None listed",
  max,
}: {
  items: string[];
  tone?: Tone;
  empty?: string;
  max?: number;
}) {
  if (!items?.length) {
    return <span className="text-sm text-slate-400">{empty}</span>;
  }
  const shown = max ? items.slice(0, max) : items;
  return (
    <div className="flex flex-wrap gap-1.5">
      {shown.map((item) => (
        <Badge key={item} tone={tone}>
          {item}
        </Badge>
      ))}
      {max && items.length > max ? (
        <Badge tone="slate">+{items.length - max}</Badge>
      ) : null}
    </div>
  );
}

// --- Controls ----------------------------------------------------------------

type ButtonProps = {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: "primary" | "secondary" | "danger" | "success" | "warning" | "ghost";
  disabled?: boolean;
  size?: "sm" | "md";
  className?: string;
};

const BUTTON_VARIANT: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary: "bg-slate-900 text-white hover:bg-slate-800",
  secondary:
    "bg-white text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50",
  danger: "bg-rose-600 text-white hover:bg-rose-500",
  success: "bg-emerald-600 text-white hover:bg-emerald-500",
  warning: "bg-amber-500 text-white hover:bg-amber-400",
  ghost: "text-slate-600 hover:bg-slate-100",
};

export function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled,
  size = "md",
  className,
}: ButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cx(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3.5 py-2 text-sm",
        BUTTON_VARIANT[variant],
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-700">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-xs text-slate-500">{hint}</span> : null}
    </label>
  );
}

const CONTROL_CLASS =
  "mt-1 w-full rounded-lg border-0 bg-white px-3 py-2 text-sm text-slate-900 ring-1 ring-inset ring-slate-300 " +
  "placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-slate-900 disabled:bg-slate-50";

export function Input(props: {
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  min?: string;
  step?: string;
}) {
  const { onChange, ...rest } = props;
  return (
    <input
      {...rest}
      className={CONTROL_CLASS}
      onChange={(event: ChangeEvent<HTMLInputElement>) =>
        onChange(event.target.value)
      }
    />
  );
}

export function Textarea(props: {
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
}) {
  const { onChange, rows = 4, ...rest } = props;
  return (
    <textarea
      {...rest}
      rows={rows}
      className={CONTROL_CLASS}
      onChange={(event: ChangeEvent<HTMLTextAreaElement>) =>
        onChange(event.target.value)
      }
    />
  );
}

export function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className={CONTROL_CLASS}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

// --- Table -------------------------------------------------------------------

/**
 * Responsive table.
 *
 * Above `md` it is an ordinary table. Below it, `globals.css` turns each row
 * into a card and each cell into a "Label — value" line; the labels come from
 * each `Td`'s own `label` prop. Pass `label=""` for a trailing actions column
 * so it spans the card instead of growing a heading.
 */
export function Table({
  headers,
  children,
}: {
  headers: string[];
  children: ReactNode;
}) {
  return (
    <div className="overflow-x-auto px-4 pb-4 md:px-0 md:pb-0">
      <table className="rtable w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-100">
            {headers.map((header, index) => (
              <th
                key={`${header}-${index}`}
                className="px-5 py-2.5 text-xs font-medium uppercase tracking-wide text-slate-500"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="rtable-body">{children}</tbody>
      </table>
    </div>
  );
}

export function Td({
  children,
  className,
  label = "",
}: {
  children: ReactNode;
  className?: string;
  /** The column heading, repeated per cell so the mobile card can show it. */
  label?: string;
}) {
  return (
    <td data-label={label} className={cx("px-5 py-3 align-middle", className)}>
      <span className="rtable-cell">{children}</span>
    </td>
  );
}
