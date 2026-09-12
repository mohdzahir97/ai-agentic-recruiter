/**
 * Inline SVG icons.
 *
 * Hand-written rather than pulled from a package: the app needs eleven of them,
 * and a dependency for eleven paths is not worth the install. All share one
 * wrapper, use `currentColor`, and inherit size from the class you pass, so
 * they take on the colour of whatever nav item or button holds them.
 */
import type { ReactNode, SVGProps } from "react";

export type IconProps = SVGProps<SVGSVGElement> & { className?: string };

export type Icon = (props: IconProps) => ReactNode;

function Svg({
  children,
  className = "h-5 w-5",
  filled = false,
  ...rest
}: IconProps & { children: ReactNode; filled?: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke={filled ? "none" : "currentColor"}
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const DashboardIcon: Icon = (props) => (
  <Svg {...props}>
    <rect x="3" y="3" width="7.5" height="8.5" rx="1.5" />
    <rect x="13.5" y="3" width="7.5" height="5" rx="1.5" />
    <rect x="13.5" y="11" width="7.5" height="10" rx="1.5" />
    <rect x="3" y="14.5" width="7.5" height="6.5" rx="1.5" />
  </Svg>
);

export const ProfileIcon: Icon = (props) => (
  <Svg {...props}>
    <circle cx="12" cy="8" r="3.5" />
    <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
  </Svg>
);

export const ResumeIcon: Icon = (props) => (
  <Svg {...props}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5" />
    <path d="M9 13h6M9 17h4" />
  </Svg>
);

export const JobsIcon: Icon = (props) => (
  <Svg {...props}>
    <rect x="3" y="7" width="18" height="13" rx="2" />
    <path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
    <path d="M3 12h18" />
  </Svg>
);

export const ApplicationsIcon: Icon = (props) => (
  <Svg {...props}>
    <path d="M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1z" />
    <path d="M8 6H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-2" />
    <path d="M8.5 12.5l1.5 1.5 3-3.5M15 16H9" />
  </Svg>
);

export const CandidatesIcon: Icon = (props) => (
  <Svg {...props}>
    <circle cx="9" cy="8" r="3" />
    <path d="M3 19a6 6 0 0 1 12 0" />
    <path d="M16 6.5a3 3 0 0 1 0 5.5M17.5 19a6 6 0 0 0-2-4.4" />
  </Svg>
);

/** AI screening: a spark, for the one part of the product the model drives. */
export const ScreeningIcon: Icon = (props) => (
  <Svg {...props}>
    <path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6z" />
    <path d="M18.5 15.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z" />
  </Svg>
);

export const MenuIcon: Icon = (props) => (
  <Svg {...props}>
    <path d="M4 6h16M4 12h16M4 18h16" />
  </Svg>
);

export const CloseIcon: Icon = (props) => (
  <Svg {...props}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Svg>
);

/** Points the way the panel will move, so the button reads as its own action. */
export const CollapseIcon: Icon = (props) => (
  <Svg {...props}>
    <path d="M14 7l-5 5 5 5" />
    <path d="M19 4v16" />
  </Svg>
);

export const ExpandIcon: Icon = (props) => (
  <Svg {...props}>
    <path d="M10 7l5 5-5 5" />
    <path d="M5 4v16" />
  </Svg>
);

export const LogoutIcon: Icon = (props) => (
  <Svg {...props}>
    <path d="M15 17l5-5-5-5" />
    <path d="M20 12H9" />
    <path d="M12 20H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h6" />
  </Svg>
);

export const ChevronDownIcon: Icon = (props) => (
  <Svg {...props}>
    <path d="M6 9l6 6 6-6" />
  </Svg>
);
