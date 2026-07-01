import type { AttachedProfile, Profile } from "../types";

const CHAT_REQUEST_LIMIT = 8000;

const PILLAR_LABELS: Array<[keyof Profile["pillars"], string]> = [
  ["year", "年柱"],
  ["month", "月柱"],
  ["day", "日柱"],
  ["hour", "时柱"],
];

function compactDatePart(value: number | null | undefined): string {
  return value == null ? "" : String(value);
}

export function compactBirth(profile: Profile): string {
  const birth = profile.birth;
  if (!birth || !birth.year || !birth.month || !birth.day) {
    return "出生信息待补充";
  }
  const time =
    birth.hour == null
      ? ""
      : ` ${String(birth.hour).padStart(2, "0")}:${String(birth.minute ?? 0).padStart(2, "0")}`;
  const calendar = birth.calendar_type === "lunar" ? "农历" : "公历";
  const place = [birth.province, birth.city].filter(Boolean).join("");
  return `${calendar} ${compactDatePart(birth.year)}-${compactDatePart(birth.month)}-${compactDatePart(birth.day)}${time}${place ? ` · ${place}` : ""}`;
}

export function compactPillars(profile: Profile): string {
  const items = PILLAR_LABELS.map(([field, label]) => {
    const value = profile.pillars[field];
    return value ? `${label}${value}` : "";
  }).filter(Boolean);
  return items.length ? items.join("，") : "四柱待排";
}

function compactFiveElements(profile: Profile): string {
  if (!profile.five_elements) {
    return "";
  }
  const items = Object.entries(profile.five_elements)
    .filter(([, value]) => typeof value === "number")
    .map(([name, value]) => `${name}${value}`);
  return items.length ? `五行${items.join("，")}` : "";
}

export function toAttachedProfile(profile: Profile): AttachedProfile {
  return {
    id: profile.id,
    name: profile.name,
    relationship_type: profile.relationship_type,
  };
}

function profilePromptLine(profile: Profile, index: number): string {
  const parts = [
    `${profile.relationship_type}：${profile.name}`,
    profile.gender ? `性别${profile.gender}` : "",
    compactBirth(profile),
    compactPillars(profile),
    compactFiveElements(profile),
  ].filter(Boolean);
  return `${index + 1}. ${parts.join("；")}`;
}

export function buildProfilePrompt(message: string, profiles: Profile[]): string {
  if (profiles.length === 0) {
    return message;
  }

  const header = "本轮问题请优先参考以下已选择的人物档案，未选择的档案不要作为本轮依据：\n";
  const footer = `\n\n用户问题：\n${message}`;
  const budget = CHAT_REQUEST_LIMIT - header.length - footer.length - 80;
  if (budget <= 0) {
    return message;
  }

  const lines: string[] = [];
  let used = 0;
  profiles.forEach((profile, index) => {
    const full = profilePromptLine(profile, index);
    const minimal = `${index + 1}. ${profile.relationship_type}：${profile.name}`;
    const next = used + full.length + 1 <= budget ? full : minimal;
    if (used + next.length + 1 <= budget) {
      lines.push(next);
      used += next.length + 1;
    }
  });

  if (lines.length === 0) {
    return message;
  }
  const omitted = profiles.length - lines.length;
  const omittedText = omitted > 0 ? `\n（另有 ${omitted} 位档案因长度限制未展开。）` : "";
  return `${header}${lines.join("\n")}${omittedText}${footer}`;
}
