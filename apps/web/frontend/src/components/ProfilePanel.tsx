import { useEffect, useMemo, useState } from "react";
import type { KeyboardEvent } from "react";
import {
  App as AntdApp,
  Button,
  Cascader,
  Checkbox,
  Empty,
  Form,
  Input,
  Modal,
  Segmented,
  Select,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { CheckCircleFilled, EditOutlined, PlusOutlined } from "@ant-design/icons";
import type { Profile, ProfilePayload } from "../types";
import { compactBirth } from "../lib/profileText";

const PILLAR_LABELS: Array<[keyof Profile["pillars"], string]> = [
  ["year", "年"],
  ["month", "月"],
  ["day", "日"],
  ["hour", "时"],
];

const RELATION_OPTIONS = ["本人", "父亲", "母亲", "伴侣", "子女", "朋友", "其他"].map((value) => ({
  label: value,
  value,
}));

const GENDER_OPTIONS = ["男", "女", "未知"].map((value) => ({ label: value, value }));

const CALENDAR_OPTIONS = [
  { label: "公历", value: "solar" },
  { label: "农历", value: "lunar" },
];

type CascaderValue = Array<string | number>;
interface CascaderOption {
  label: string;
  value: string | number;
  children?: CascaderOption[];
}

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: CURRENT_YEAR - 1899 + 6 }, (_, index) => {
  const value = 1900 + index;
  return value;
}).reverse();
const DATE_OPTIONS: CascaderOption[] = YEARS.map((year) => ({
  label: `${year}年`,
  value: year,
  children: Array.from({ length: 12 }, (_, monthIndex) => {
    const month = monthIndex + 1;
    const dayCount = new Date(year, month, 0).getDate();
    return {
      label: `${month}月`,
      value: month,
      children: Array.from({ length: dayCount }, (_, dayIndex) => {
        const day = dayIndex + 1;
        return { label: `${day}日`, value: day };
      }),
    };
  }),
}));
const TIME_OPTIONS: CascaderOption[] = Array.from({ length: 24 }, (_, hour) => ({
  label: `${String(hour).padStart(2, "0")}时`,
  value: hour,
  children: Array.from({ length: 60 }, (_, minute) => ({
    label: `${String(minute).padStart(2, "0")}分`,
    value: minute,
  })),
}));
const FALLBACK_LOCATION_OPTIONS: CascaderOption[] = ["北京市", "上海市", "天津市", "重庆市"].map(
  (value) => ({
    label: value,
    value,
    children: [{ label: value, value }],
  }),
);

interface ProfileFormValues {
  name: string;
  relationship_type: string;
  gender?: string | null;
  birth_date?: CascaderValue;
  birth_time?: CascaderValue;
  calendar_type?: string | null;
  is_leap_month?: boolean | null;
  location?: CascaderValue;
}

interface ProfilePanelProps {
  sessionId: string;
  profiles: Profile[];
  selectedProfileIds: number[];
  onSelectedProfileIdsChange: (ids: number[]) => void;
  onChanged: () => void;
}

function toPayload(values: ProfileFormValues): ProfilePayload {
  const birthDate = values.birth_date ?? [];
  const birthTime = values.birth_time ?? [];
  const location = values.location ?? [];
  const birthHour = typeof birthTime[0] === "number" ? birthTime[0] : null;
  const birthMinute = typeof birthTime[1] === "number" ? birthTime[1] : null;

  return {
    name: values.name.trim(),
    relationship_type: values.relationship_type || "本人",
    gender: values.gender || null,
    birth_year: typeof birthDate[0] === "number" ? birthDate[0] : null,
    birth_month: typeof birthDate[1] === "number" ? birthDate[1] : null,
    birth_day: typeof birthDate[2] === "number" ? birthDate[2] : null,
    birth_hour: birthHour,
    birth_minute: birthHour === null ? null : birthMinute ?? 0,
    calendar_type: values.calendar_type || null,
    is_leap_month: values.is_leap_month ?? null,
    province: typeof location[0] === "string" ? location[0] : null,
    city: typeof location[1] === "string" ? location[1] : null,
    longitude: null,
  };
}

function compactCascaderValue(parts: Array<string | number | null | undefined>): CascaderValue | undefined {
  const value = parts.filter((part) => part !== null && part !== undefined) as CascaderValue;
  return value.length > 0 ? value : undefined;
}

function fromProfile(profile?: Profile): ProfileFormValues {
  if (!profile) {
    return {
      name: "",
      relationship_type: "本人",
      gender: "未知",
      birth_time: undefined,
      calendar_type: "solar",
      is_leap_month: false,
      location: undefined,
    };
  }
  return {
    name: profile.name,
    relationship_type: profile.relationship_type,
    gender: profile.gender ?? "未知",
    birth_date: compactCascaderValue([
      profile.birth?.year,
      profile.birth?.month,
      profile.birth?.day,
    ]),
    birth_time:
      profile.birth?.hour === null || profile.birth?.hour === undefined
        ? undefined
        : [profile.birth.hour, profile.birth.minute ?? 0],
    calendar_type: profile.birth?.calendar_type ?? "solar",
    is_leap_month: profile.birth?.is_leap_month ?? false,
    location: compactCascaderValue([profile.birth?.province, profile.birth?.city]),
  };
}

export function ProfilePanel({
  sessionId,
  profiles,
  selectedProfileIds,
  onSelectedProfileIdsChange,
  onChanged,
}: ProfilePanelProps) {
  const { message } = AntdApp.useApp();
  const [form] = Form.useForm<ProfileFormValues>();
  const [editing, setEditing] = useState<Profile | null>(null);
  const [formValues, setFormValues] = useState<ProfileFormValues>(() => fromProfile());
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [locationOptions, setLocationOptions] = useState<CascaderOption[]>(
    FALLBACK_LOCATION_OPTIONS,
  );
  const calendarType = Form.useWatch("calendar_type", form);

  const selectedSet = useMemo(() => new Set(selectedProfileIds), [selectedProfileIds]);
  const selectedCount = profiles.filter((profile) => selectedSet.has(profile.id)).length;
  const selectedNameText = profiles
    .filter((profile) => selectedSet.has(profile.id))
    .map((profile) => profile.name)
    .slice(0, 3)
    .join("、");
  const selectedSummary =
    selectedCount > 3 ? `${selectedNameText}等${selectedCount}人` : selectedNameText;
  const modalTitle = useMemo(() => (editing ? "编辑人物信息" : "新增人物"), [editing]);

  const setProfileSelected = (profileId: number, selected: boolean) => {
    const next = new Set(selectedProfileIds);
    if (selected) {
      next.add(profileId);
    } else {
      next.delete(profileId);
    }
    onSelectedProfileIdsChange([...next]);
  };

  const clearSelection = () => {
    onSelectedProfileIdsChange([]);
  };

  const openCreate = () => {
    const values = fromProfile();
    setEditing(null);
    setFormValues(values);
    form.setFieldsValue(values);
    setModalOpen(true);
  };

  const openEdit = (profile: Profile) => {
    const values = fromProfile(profile);
    setEditing(profile);
    setFormValues(values);
    form.setFieldsValue(values);
    setModalOpen(true);
  };

  useEffect(() => {
    let cancelled = false;
    fetch("/api/profiles/meta/cities")
      .then((response) => {
        if (!response.ok) {
          throw new Error("city options unavailable");
        }
        return response.json();
      })
      .then((payload) => {
        if (!cancelled && Array.isArray(payload?.options) && payload.options.length > 0) {
          setLocationOptions(payload.options);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLocationOptions(FALLBACK_LOCATION_OPTIONS);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (modalOpen) {
      form.setFieldsValue(formValues);
    }
  }, [form, formValues, modalOpen]);

  const handleItemKeyDown = (event: KeyboardEvent<HTMLElement>, profileId: number) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      setProfileSelected(profileId, !selectedSet.has(profileId));
    }
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const payload = toPayload(values);
      const url = editing
        ? `/api/profiles/${encodeURIComponent(sessionId)}/${editing.id}`
        : `/api/profiles/${encodeURIComponent(sessionId)}`;
      const response = await fetch(url, {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error("保存人物信息失败");
      }
      const result = await response.json().catch(() => null);
      const savedId = Number(result?.profile?.id);
      message.success("人物信息已保存");
      setModalOpen(false);
      if (!editing && Number.isFinite(savedId)) {
        onSelectedProfileIdsChange([...new Set([...selectedProfileIds, savedId])]);
      }
      onChanged();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存人物信息失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="profile-panel profile-picker-panel">
      <header className="profile-panel-head profile-picker-head">
        <div>
          <Typography.Title level={5}>提问档案</Typography.Title>
          <Typography.Text type="secondary">
            {profiles.length === 0
              ? "暂无人物"
              : selectedCount > 0
                ? `已附加 ${selectedSummary}`
                : "选择本轮要参考的人物"}
          </Typography.Text>
        </div>
        <Button type="primary" size="small" icon={<PlusOutlined />} onClick={openCreate}>
          新增
        </Button>
      </header>

      {profiles.length > 0 && (
        <div className="profile-picker-toolbar">
          <Button size="small" disabled={selectedCount === 0} onClick={clearSelection}>
            清空已附加
          </Button>
        </div>
      )}

      {profiles.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="还没有人物档案"
          className="profile-empty"
        >
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新增人物
          </Button>
        </Empty>
      ) : (
        <div className="profile-picker-list">
          {profiles.map((profile) => {
            const selected = selectedSet.has(profile.id);
            return (
              <article
                key={profile.id}
                className={`profile-picker-item${selected ? " is-selected" : ""}`}
                role="checkbox"
                aria-checked={selected}
                tabIndex={0}
                onClick={() => setProfileSelected(profile.id, !selected)}
                onKeyDown={(event) => handleItemKeyDown(event, profile.id)}
              >
                <div className="profile-picker-check">
                  {selected ? (
                    <CheckCircleFilled aria-hidden="true" />
                  ) : (
                    <Checkbox
                      checked={false}
                      onClick={(event) => event.stopPropagation()}
                      onChange={(event) => setProfileSelected(profile.id, event.target.checked)}
                    />
                  )}
                </div>
                <div className="profile-picker-main">
                  <div className="profile-picker-title">
                    <span className="profile-name">{profile.name}</span>
                    <Tag className="profile-relation-tag">{profile.relationship_type}</Tag>
                    {selected ? <Tag className="profile-selected-tag">已附加</Tag> : null}
                  </div>
                  <p className="profile-birth">{compactBirth(profile)}</p>
                  <div className="profile-pillars">
                    {PILLAR_LABELS.map(([field, label]) => (
                      <span key={field} className="profile-pillar">
                        <em>{label}</em>
                        {profile.pillars[field] ?? "待排"}
                      </span>
                    ))}
                  </div>
                </div>
                <Tooltip title="编辑人物信息">
                  <Button
                    size="small"
                    type="default"
                    icon={<EditOutlined />}
                    className="profile-edit"
                    aria-label={`编辑${profile.name}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      openEdit(profile);
                    }}
                  >
                    编辑
                  </Button>
                </Tooltip>
              </article>
            );
          })}
        </div>
      )}

      <Modal
        title={modalTitle}
        open={modalOpen}
        okText="保存"
        cancelText="取消"
        width={560}
        className="profile-modal"
        confirmLoading={saving}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          className="profile-form"
          preserve={false}
          initialValues={formValues}
        >
          <div className="profile-form-hero">
            <span className="profile-form-hero-kicker">{editing ? "正在编辑" : "新建档案"}</span>
            <strong>{editing?.name ?? "填写人物信息"}</strong>
            <span>{editing ? compactBirth(editing) : "保存后可在提问时一键附加"}</span>
          </div>

          <div className="profile-form-section">
            <Typography.Text className="profile-form-section-title">基础信息</Typography.Text>
            <Form.Item name="name" label="姓名" rules={[{ required: true, message: "请输入姓名" }]}>
              <Input maxLength={64} placeholder="输入人物姓名" autoFocus />
            </Form.Item>
            <div className="profile-form-grid">
              <Form.Item name="relationship_type" label="关系">
                <Select options={RELATION_OPTIONS} popupMatchSelectWidth={false} />
              </Form.Item>
              <Form.Item name="gender" label="性别">
                <Segmented block options={GENDER_OPTIONS} />
              </Form.Item>
            </div>
          </div>

          <div className="profile-form-section">
            <Typography.Text className="profile-form-section-title">出生信息</Typography.Text>
            <div className="profile-form-grid compact">
              <Form.Item name="calendar_type" label="历法">
                <Segmented block options={CALENDAR_OPTIONS} />
              </Form.Item>
              {calendarType === "lunar" ? (
                <Form.Item name="is_leap_month" label="闰月">
                  <Select
                    options={[
                      { label: "非闰月", value: false },
                      { label: "闰月", value: true },
                    ]}
                    popupMatchSelectWidth={false}
                  />
                </Form.Item>
              ) : null}
            </div>
            <Form.Item name="birth_date" label="出生日期">
              <Cascader
                allowClear
                changeOnSelect
                options={DATE_OPTIONS}
                placeholder="选择年 / 月 / 日"
                showSearch
              />
            </Form.Item>
            <Form.Item name="birth_time" label="出生时间">
              <Cascader
                allowClear
                changeOnSelect
                options={TIME_OPTIONS}
                placeholder="选择小时 / 分钟"
                showSearch
              />
            </Form.Item>
          </div>

          <div className="profile-form-section">
            <Typography.Text className="profile-form-section-title">出生地</Typography.Text>
            <Form.Item name="location" label="省市">
              <Cascader
                allowClear
                changeOnSelect
                options={locationOptions}
                placeholder="选择省份 / 城市"
                showSearch
              />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </section>
  );
}
