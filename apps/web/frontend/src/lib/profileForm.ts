import type { Profile, ProfilePayload } from "../types";

export const RELATION_VALUES = ["本人", "父亲", "母亲", "伴侣", "子女", "朋友", "其他"] as const;
export const RELATION_OPTIONS = RELATION_VALUES.map((value) => ({ label: value, value }));
export const GENDER_OPTIONS = ["男", "女", "未知"].map((value) => ({ label: value, value }));
export const CALENDAR_OPTIONS = [
  { label: "公历", value: "solar" },
  { label: "农历", value: "lunar" },
];

export type CascaderValue = Array<string | number>;
export interface CascaderOption {
  label: string;
  value: string | number;
  children?: CascaderOption[];
}

export interface ProfileFormValues {
  name: string;
  relationship_type: string;
  custom_relationship?: string | null;
  gender?: string | null;
  birth_date?: CascaderValue;
  birth_time?: CascaderValue;
  calendar_type?: string | null;
  is_leap_month?: boolean | null;
  location?: CascaderValue;
}

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: CURRENT_YEAR - 1899 + 6 }, (_, index) => 1900 + index).reverse();

export const DATE_OPTIONS: CascaderOption[] = YEARS.map((year) => ({
  label: `${year}年`,
  value: year,
  children: Array.from({ length: 12 }, (_, monthIndex) => {
    const month = monthIndex + 1;
    const dayCount = new Date(year, month, 0).getDate();
    return {
      label: `${month}月`,
      value: month,
      children: Array.from({ length: dayCount }, (_, dayIndex) => ({
        label: `${dayIndex + 1}日`,
        value: dayIndex + 1,
      })),
    };
  }),
}));

export const TIME_OPTIONS: CascaderOption[] = Array.from({ length: 24 }, (_, hour) => ({
  label: `${String(hour).padStart(2, "0")}时`,
  value: hour,
  children: Array.from({ length: 60 }, (_, minute) => ({
    label: `${String(minute).padStart(2, "0")}分`,
    value: minute,
  })),
}));

export const FALLBACK_LOCATION_OPTIONS: CascaderOption[] = ["北京市", "上海市", "天津市", "重庆市"].map(
  (value) => ({ label: value, value, children: [{ label: value, value }] }),
);

function compact(parts: Array<string | number | null | undefined>): CascaderValue | undefined {
  const value = parts.filter((part) => part !== null && part !== undefined) as CascaderValue;
  return value.length > 0 ? value : undefined;
}

export function profileToForm(profile?: Profile, relationshipType = "本人"): ProfileFormValues {
  if (!profile) {
    return {
      name: "",
      relationship_type: relationshipType,
      custom_relationship: null,
      gender: "未知",
      calendar_type: "solar",
      is_leap_month: false,
    };
  }
  return {
    name: profile.name,
    relationship_type: profile.relationship_type,
    custom_relationship: profile.custom_relationship ?? null,
    gender: profile.gender ?? "未知",
    birth_date: compact([profile.birth?.year, profile.birth?.month, profile.birth?.day]),
    birth_time:
      profile.birth?.hour === null || profile.birth?.hour === undefined
        ? undefined
        : [profile.birth.hour, profile.birth.minute ?? 0],
    calendar_type: profile.birth?.calendar_type ?? "solar",
    is_leap_month: profile.birth?.is_leap_month ?? false,
    location: compact([profile.birth?.province, profile.birth?.city]),
  };
}

export function formToProfilePayload(values: ProfileFormValues): ProfilePayload {
  const birthDate = values.birth_date ?? [];
  const birthTime = values.birth_time ?? [];
  const location = values.location ?? [];
  const birthHour = typeof birthTime[0] === "number" ? birthTime[0] : null;
  return {
    name: values.name.trim(),
    relationship_type: values.relationship_type,
    custom_relationship:
      values.relationship_type === "其他" ? values.custom_relationship?.trim() || null : null,
    gender: values.gender || null,
    birth_year: typeof birthDate[0] === "number" ? birthDate[0] : null,
    birth_month: typeof birthDate[1] === "number" ? birthDate[1] : null,
    birth_day: typeof birthDate[2] === "number" ? birthDate[2] : null,
    birth_hour: birthHour,
    birth_minute: birthHour === null ? null : typeof birthTime[1] === "number" ? birthTime[1] : 0,
    calendar_type: values.calendar_type || null,
    is_leap_month: values.is_leap_month ?? null,
    province: typeof location[0] === "string" ? location[0] : null,
    city: typeof location[1] === "string" ? location[1] : null,
    longitude: null,
  };
}
