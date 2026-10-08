import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement> & { size?: number };

function base({ size = 16, ...p }: P, path: React.ReactNode) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...p}
    >
      {path}
    </svg>
  );
}

export const IconDashboard = (p: P) =>
  base(p, (
    <>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </>
  ));

export const IconCamera = (p: P) =>
  base(p, (
    <>
      <path d="M4 8h2.5l1.7-2.5h7.6L17.5 8H20a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 20 20H4a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 4 8Z" />
      <circle cx="12" cy="14" r="3.4" />
    </>
  ));

export const IconHistory = (p: P) =>
  base(p, (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </>
  ));

export const IconBook = (p: P) =>
  base(p, (
    <>
      <path d="M4 5.5A2 2 0 0 1 6 3.5h13v15H6a2 2 0 0 0-2 2Z" />
      <path d="M4 18.5V5.5" />
      <path d="M8 7.5h7M8 11h7" />
    </>
  ));

export const IconChart = (p: P) =>
  base(p, (
    <>
      <path d="M4 20V10M10 20V4M16 20v-7M21 20H3" />
    </>
  ));

export const IconSettings = (p: P) =>
  base(p, (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19 12a7 7 0 0 0-.1-1.1l2-1.5-2-3.4-2.3 1a7 7 0 0 0-1.9-1.1L14.3 3h-4l-.4 2.8a7 7 0 0 0-1.9 1.1l-2.3-1-2 3.4 2 1.5a7 7 0 0 0 0 2.2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 1.9 1.1l.4 2.8h4l.4-2.8a7 7 0 0 0 1.9-1.1l2.3 1 2-3.4-2-1.5c.06-.36.1-.73.1-1.1Z" />
    </>
  ));

export const IconUsers = (p: P) =>
  base(p, (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M3.5 19.5a5.5 5.5 0 0 1 11 0" />
      <path d="M16 5a3.5 3.5 0 0 1 0 7M17.5 19.5a5.5 5.5 0 0 0-2.2-4.4" />
    </>
  ));

export const IconSearch = (p: P) =>
  base(p, (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.5 4.5" />
    </>
  ));

export const IconBell = (p: P) =>
  base(p, (
    <>
      <path d="M6 9a6 6 0 0 1 12 0c0 4 1.5 5.5 1.5 5.5h-15S6 13 6 9Z" />
      <path d="M10 18a2 2 0 0 0 4 0" />
    </>
  ));

export const IconSun = (p: P) =>
  base(p, (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5 5l1.4 1.4M17.6 17.6 19 19M19 5l-1.4 1.4M6.4 17.6 5 19" />
    </>
  ));

export const IconMoon = (p: P) =>
  base(p, <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" />);

export const IconMonitor = (p: P) =>
  base(p, (
    <>
      <rect x="3" y="4.5" width="18" height="12" rx="1.8" />
      <path d="M9 20.5h6M12 16.5v4" />
    </>
  ));

export const IconChevronDown = (p: P) =>
  base(p, <path d="m6 9.5 6 6 6-6" />);

export const IconChevronRight = (p: P) =>
  base(p, <path d="m9.5 6 6 6-6 6" />);

export const IconArrowLeft = (p: P) =>
  base(p, (
    <>
      <path d="M19 12H5" />
      <path d="m11 6-6 6 6 6" />
    </>
  ));

export const IconCheck = (p: P) => base(p, <path d="m5 12.5 4.5 4.5L19 7" />);

export const IconX = (p: P) => base(p, <path d="M6 6l12 12M18 6 6 18" />);

export const IconAlert = (p: P) =>
  base(p, (
    <>
      <path d="M12 3.5 2.8 19.5h18.4L12 3.5Z" />
      <path d="M12 9.5v4.5M12 17h.01" />
    </>
  ));

export const IconInfo = (p: P) =>
  base(p, (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11v5M12 8h.01" />
    </>
  ));

export const IconHelp = (p: P) =>
  base(p, (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M9.5 9.5a2.5 2.5 0 1 1 3.4 2.3c-.6.3-.9.8-.9 1.4v.6M12 16.8h.01" />
    </>
  ));

export const IconUpload = (p: P) =>
  base(p, (
    <>
      <path d="M12 15V4M8 7.5 12 3.5l4 4" />
      <path d="M4.5 15v3.5A1.5 1.5 0 0 0 6 20h12a1.5 1.5 0 0 0 1.5-1.5V15" />
    </>
  ));

export const IconMenu = (p: P) =>
  base(p, <path d="M4 7h16M4 12h16M4 17h16" />);

export const IconTrash = (p: P) =>
  base(p, (
    <>
      <path d="M4.5 6.5h15M9.5 6.5V5a1.5 1.5 0 0 1 1.5-1.5h2A1.5 1.5 0 0 1 14.5 5v1.5" />
      <path d="M6.5 6.5 7.4 19a1.5 1.5 0 0 0 1.5 1.4h6.2a1.5 1.5 0 0 0 1.5-1.4l.9-12.5" />
      <path d="M10 10.5v6M14 10.5v6" />
    </>
  ));

export const IconSparkle = (p: P) =>
  base(p, (
    <path d="M12 3.5 13.8 9l5.5 1.8-5.5 1.8L12 18l-1.8-5.4L4.7 10.8 10.2 9 12 3.5Z" />
  ));

export const IconClock = (p: P) =>
  base(p, (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3.5 2" />
    </>
  ));

export const IconLayers = (p: P) =>
  base(p, (
    <>
      <path d="m12 3.5 8.5 4.7L12 13l-8.5-4.8L12 3.5Z" />
      <path d="m4 13.2 8 4.4 8-4.4M4 17l8 4.4L20 17" />
    </>
  ));

export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <span className="brand-mark" style={{ width: size, height: size }}>
      <svg
        width={size * 0.62}
        height={size * 0.62}
        viewBox="0 0 32 32"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M16 26c-6-2.4-9.5-7-9.5-12.8C11.2 13.2 16 14.4 18.4 18c2.4-3.6 3.6-8.4 3.6-13.2C26 8.2 27 13 27 16.6c0 4.7-3.6 8.2-11 9.4z" />
      </svg>
    </span>
  );
}
