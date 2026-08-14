import { useEffect, useMemo, useState } from "react";
import {
  App as AntdApp,
  Button,
  Cascader,
  Form,
  Input,
  Segmented,
  Select,
} from "antd";
import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import type { Profile, ProfileCandidate } from "../types";
import {
  CALENDAR_OPTIONS,
  DATE_OPTIONS,
  FALLBACK_LOCATION_OPTIONS,
  GENDER_OPTIONS,
  RELATION_OPTIONS,
  TIME_OPTIONS,
  formToProfilePayload,
  profileToForm,
  type CascaderOption,
  type ProfileFormValues,
} from "../lib/profileForm";

interface ProfileEditorProps {
  profile?: Profile;
  candidate?: ProfileCandidate;
  initialRelationship?: string;
  onCancel: () => void;
  onSaved: (profile: Profile) => void;
}

function candidateInitialValues(candidate: ProfileCandidate): ProfileFormValues {
  const suggested = candidate.suggested_relationship || "";
  const matched = RELATION_OPTIONS.some((option) => option.value === suggested);
  return {
    ...profileToForm(undefined, matched ? suggested : "其他"),
    name: candidate.display_name.startsWith("我的") ? "" : candidate.display_name,
    custom_relationship: matched ? null : suggested || null,
  };
}

export function ProfileEditor({
  profile,
  candidate,
  initialRelationship = "本人",
  onCancel,
  onSaved,
}: ProfileEditorProps) {
  const { message } = AntdApp.useApp();
  const [form] = Form.useForm<ProfileFormValues>();
  const [saving, setSaving] = useState(false);
  const [locationOptions, setLocationOptions] = useState<CascaderOption[]>(
    FALLBACK_LOCATION_OPTIONS,
  );
  const relationshipType = Form.useWatch("relationship_type", form);
  const calendarType = Form.useWatch("calendar_type", form);
  const initialValues = useMemo(
    () => candidate ? candidateInitialValues(candidate) : profileToForm(profile, initialRelationship),
    [candidate, initialRelationship, profile],
  );

  useEffect(() => {
    form.setFieldsValue(initialValues);
  }, [form, initialValues]);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/profiles/meta/cities", { credentials: "include" })
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((payload) => {
        if (!cancelled && Array.isArray(payload.options) && payload.options.length > 0) {
          setLocationOptions(payload.options);
        }
      })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    const payload = formToProfilePayload(values);
    setSaving(true);
    try {
      const endpoint = candidate
        ? `/api/profile-candidates/${candidate.id}/convert`
        : profile
          ? `/api/profiles/${profile.id}`
          : "/api/profiles";
      const response = await fetch(endpoint, {
        method: profile && !candidate ? "PUT" : "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(result?.detail || "保存人物档案失败");
      }
      message.success(candidate ? "已加入人物档案" : "人物档案已保存");
      onSaved(result.profile as Profile);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存人物档案失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="profile-editor">
      <header className="profile-module-header">
        <Button type="text" icon={<ArrowLeftOutlined />} aria-label="返回人物档案" onClick={onCancel} />
        <div className="profile-module-title">
          <h1>{profile ? "编辑人物档案" : candidate ? "补充人物资料" : "新增人物档案"}</h1>
          <p>{candidate ? "确认姓名和关系后，才会保存为正式档案" : "姓名和与本人关系为必填项"}</p>
        </div>
      </header>

      <div className="profile-editor-scroll">
        <Form form={form} layout="vertical" className="profile-editor-form" initialValues={initialValues}>
          <section className="profile-editor-section" aria-labelledby="profile-basic-heading">
            <h2 id="profile-basic-heading">基础信息</h2>
            <div className="profile-editor-grid">
              <Form.Item name="name" label="姓名" rules={[{ required: true, whitespace: true, message: "请输入人物姓名" }]}>
                <Input maxLength={64} placeholder="输入姓名" autoFocus />
              </Form.Item>
              <Form.Item name="relationship_type" label="与本人关系" rules={[{ required: true, message: "请选择与本人关系" }]}>
                <Select options={RELATION_OPTIONS} />
              </Form.Item>
            </div>
            {relationshipType === "其他" ? (
              <Form.Item name="custom_relationship" label="关系说明" rules={[{ required: true, whitespace: true, message: "请输入关系说明" }]}>
                <Input maxLength={40} placeholder="例如：同事、同学、兄弟姐妹" />
              </Form.Item>
            ) : null}
            <Form.Item name="gender" label="性别">
              <Segmented options={GENDER_OPTIONS} />
            </Form.Item>
          </section>

          <section className="profile-editor-section" aria-labelledby="profile-birth-heading">
            <h2 id="profile-birth-heading">出生信息</h2>
            <div className="profile-editor-grid">
              <Form.Item name="calendar_type" label="历法">
                <Segmented block options={CALENDAR_OPTIONS} />
              </Form.Item>
              {calendarType === "lunar" ? (
                <Form.Item name="is_leap_month" label="闰月">
                  <Select options={[{ label: "非闰月", value: false }, { label: "闰月", value: true }]} />
                </Form.Item>
              ) : <span />}
              <Form.Item name="birth_date" label="出生日期">
                <Cascader allowClear changeOnSelect options={DATE_OPTIONS} placeholder="选择年 / 月 / 日" />
              </Form.Item>
              <Form.Item name="birth_time" label="出生时间">
                <Cascader allowClear changeOnSelect options={TIME_OPTIONS} placeholder="选择小时 / 分钟" />
              </Form.Item>
            </div>
            <p className="profile-editor-note">出生资料可以稍后补充；资料不完整时暂不能排盘。</p>
          </section>

          <section className="profile-editor-section" aria-labelledby="profile-location-heading">
            <h2 id="profile-location-heading">出生地</h2>
            <Form.Item name="location" label="省市">
              <Cascader allowClear changeOnSelect options={locationOptions} placeholder="选择省份 / 城市" />
            </Form.Item>
          </section>
        </Form>
      </div>

      <footer className="profile-editor-actions">
        <Button onClick={onCancel}>取消</Button>
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={() => void handleSave()}>
          保存<span className="profile-save-wide-label">档案</span>
        </Button>
      </footer>
    </section>
  );
}
