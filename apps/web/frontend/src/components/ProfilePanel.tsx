import { useMemo, useState } from "react";
import type { KeyboardEvent } from "react";
import {
  App as AntdApp,
  AutoComplete,
  Button,
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
import { EditOutlined, PlusOutlined } from "@ant-design/icons";
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

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: CURRENT_YEAR - 1899 + 6 }, (_, index) => {
  const value = 1900 + index;
  return { label: `${value}年`, value };
}).reverse();
const MONTH_OPTIONS = Array.from({ length: 12 }, (_, index) => {
  const value = index + 1;
  return { label: `${value}月`, value };
});
const DAY_OPTIONS = Array.from({ length: 31 }, (_, index) => {
  const value = index + 1;
  return { label: `${value}日`, value };
});
const HOUR_OPTIONS = Array.from({ length: 24 }, (_, value) => ({
  label: `${String(value).padStart(2, "0")}时`,
  value,
}));
const MINUTE_OPTIONS = Array.from({ length: 60 }, (_, value) => ({
  label: `${String(value).padStart(2, "0")}分`,
  value,
}));
const PROVINCE_OPTIONS = [
  "北京市",
  "上海市",
  "天津市",
  "重庆市",
  "广东省",
  "浙江省",
  "江苏省",
  "四川省",
  "湖北省",
  "湖南省",
  "河南省",
  "山东省",
  "陕西省",
  "福建省",
  "辽宁省",
  "黑龙江省",
].map((value) => ({ value }));
const CITY_OPTIONS = [
  "北京市",
  "上海市",
  "天津市",
  "重庆市",
  "广州市",
  "深圳市",
  "杭州市",
  "南京市",
  "成都市",
  "武汉市",
  "长沙市",
  "郑州市",
  "济南市",
  "西安市",
  "福州市",
  "沈阳市",
  "哈尔滨市",
].map((value) => ({ value }));

interface ProfileFormValues {
  name: string;
  relationship_type: string;
  gender?: string | null;
  birth_year?: number | null;
  birth_month?: number | null;
  birth_day?: number | null;
  birth_hour?: number | null;
  birth_minute?: number | null;
  calendar_type?: string | null;
  is_leap_month?: boolean | null;
  province?: string | null;
  city?: string | null;
  longitude?: string | null;
}

interface ProfilePanelProps {
  sessionId: string;
  profiles: Profile[];
  selectedProfileIds: number[];
  onSelectedProfileIdsChange: (ids: number[]) => void;
  onChanged: () => void;
}

function toPayload(values: ProfileFormValues): ProfilePayload {
  return {
    name: values.name.trim(),
    relationship_type: values.relationship_type || "本人",
    gender: values.gender || null,
    birth_year: values.birth_year ?? null,
    birth_month: values.birth_month ?? null,
    birth_day: values.birth_day ?? null,
    birth_hour: values.birth_hour ?? null,
    birth_minute: values.birth_minute ?? null,
    calendar_type: values.calendar_type || null,
    is_leap_month: values.is_leap_month ?? null,
    province: values.province?.trim() || null,
    city: values.city?.trim() || null,
    longitude: values.longitude?.trim() || null,
  };
}

function fromProfile(profile?: Profile): ProfileFormValues {
  if (!profile) {
    return {
      name: "",
      relationship_type: "本人",
      gender: "未知",
      birth_minute: 0,
      calendar_type: "solar",
      is_leap_month: false,
    };
  }
  return {
    name: profile.name,
    relationship_type: profile.relationship_type,
    gender: profile.gender ?? "未知",
    birth_year: profile.birth?.year ?? null,
    birth_month: profile.birth?.month ?? null,
    birth_day: profile.birth?.day ?? null,
    birth_hour: profile.birth?.hour ?? null,
    birth_minute: profile.birth?.minute ?? 0,
    calendar_type: profile.birth?.calendar_type ?? "solar",
    is_leap_month: profile.birth?.is_leap_month ?? false,
    province: profile.birth?.province ?? null,
    city: profile.birth?.city ?? null,
    longitude: profile.birth?.longitude ?? null,
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
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const selectedSet = useMemo(() => new Set(selectedProfileIds), [selectedProfileIds]);
  const selectedCount = profiles.filter((profile) => selectedSet.has(profile.id)).length;
  const selectedNameText = profiles
    .filter((profile) => selectedSet.has(profile.id))
    .map((profile) => profile.name)
    .slice(0, 3)
    .join("、");
  const selectedSummary =
    selectedCount > 3 ? `${selectedNameText}等${selectedCount}人` : selectedNameText;
  const allSelected = profiles.length > 0 && selectedCount === profiles.length;
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

  const toggleAll = () => {
    onSelectedProfileIdsChange(allSelected ? [] : profiles.map((profile) => profile.id));
  };

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue(fromProfile());
    setModalOpen(true);
  };

  const openEdit = (profile: Profile) => {
    setEditing(profile);
    form.setFieldsValue(fromProfile(profile));
    setModalOpen(true);
  };

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
            {profiles.length === 0 ? "暂无人物" : selectedCount > 0 ? selectedSummary : "本轮未附加档案"}
          </Typography.Text>
        </div>
        <Button type="primary" size="small" icon={<PlusOutlined />} onClick={openCreate}>
          新增
        </Button>
      </header>

      {profiles.length > 0 && (
        <div className="profile-picker-toolbar">
          <Button size="small" onClick={toggleAll}>
            {allSelected ? "取消全选" : "全选"}
          </Button>
          <Button size="small" type="text" disabled={selectedCount === 0} onClick={clearSelection}>
            清空
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
                <Checkbox
                  checked={selected}
                  onClick={(event) => event.stopPropagation()}
                  onChange={(event) => setProfileSelected(profile.id, event.target.checked)}
                />
                <div className="profile-picker-main">
                  <div className="profile-picker-title">
                    <span className="profile-name">{profile.name}</span>
                    <Tag className="profile-relation-tag">{profile.relationship_type}</Tag>
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
        <Form form={form} layout="vertical" className="profile-form" preserve={false}>
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
            <div className="profile-form-grid">
              <Form.Item name="calendar_type" label="历法">
                <Segmented block options={CALENDAR_OPTIONS} />
              </Form.Item>
              <Form.Item name="is_leap_month" label="闰月">
                <Select
                  options={[
                    { label: "非闰月", value: false },
                    { label: "闰月", value: true },
                  ]}
                  popupMatchSelectWidth={false}
                />
              </Form.Item>
            </div>
            <div className="profile-form-grid three">
              <Form.Item name="birth_year" label="年">
                <Select
                  allowClear
                  showSearch
                  options={YEAR_OPTIONS}
                  optionFilterProp="label"
                  placeholder="选择年份"
                />
              </Form.Item>
              <Form.Item name="birth_month" label="月">
                <Select allowClear options={MONTH_OPTIONS} placeholder="选择月份" />
              </Form.Item>
              <Form.Item name="birth_day" label="日">
                <Select allowClear options={DAY_OPTIONS} placeholder="选择日期" />
              </Form.Item>
            </div>
            <div className="profile-form-grid">
              <Form.Item name="birth_hour" label="时辰">
                <Select
                  allowClear
                  showSearch
                  options={HOUR_OPTIONS}
                  optionFilterProp="label"
                  placeholder="选择小时"
                />
              </Form.Item>
              <Form.Item name="birth_minute" label="分钟">
                <Select
                  allowClear
                  showSearch
                  options={MINUTE_OPTIONS}
                  optionFilterProp="label"
                  placeholder="选择分钟"
                />
              </Form.Item>
            </div>
          </div>

          <div className="profile-form-section">
            <Typography.Text className="profile-form-section-title">出生地</Typography.Text>
            <div className="profile-form-grid">
              <Form.Item name="province" label="省份">
                <AutoComplete
                  allowClear
                  options={PROVINCE_OPTIONS}
                  placeholder="选择或输入省份"
                  filterOption={(inputValue, option) =>
                    String(option?.value ?? "").includes(inputValue)
                  }
                />
              </Form.Item>
              <Form.Item name="city" label="城市">
                <AutoComplete
                  allowClear
                  options={CITY_OPTIONS}
                  placeholder="选择或输入城市"
                  filterOption={(inputValue, option) =>
                    String(option?.value ?? "").includes(inputValue)
                  }
                />
              </Form.Item>
            </div>
            <Form.Item name="longitude" label="经度校正" className="profile-form-optional">
              <Input maxLength={20} placeholder="可选，例如 116.40" />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </section>
  );
}
