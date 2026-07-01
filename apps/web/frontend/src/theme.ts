import type { ThemeConfig } from "antd";

// Palette carried over from the previous hand-written styles (teal / gold / rose)
// so the Ant Design X UI keeps the original wenjia visual identity.
export const COLORS = {
  teal: "#0f766e",
  tealDark: "#115e59",
  gold: "#b45309",
  rose: "#b91c1c",
  ink: "#1f2a2e",
};

export const theme: ThemeConfig = {
  token: {
    colorPrimary: COLORS.teal,
    colorInfo: COLORS.teal,
    colorLink: COLORS.tealDark,
    // Map antd semantic colors onto the brand palette so status Tags/Badges
    // stop rendering antd's default bright blue/green/red.
    colorSuccess: COLORS.teal,
    colorWarning: COLORS.gold,
    colorError: COLORS.rose,
    borderRadius: 10,
    fontSize: 14,
  },
};
