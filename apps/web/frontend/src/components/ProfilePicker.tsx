import { Button, Checkbox, Empty, Skeleton, Tag } from "antd";
import type { Profile } from "../types";
import { compactBirth } from "../lib/profileText";

interface ProfilePickerProps {
  profiles: Profile[];
  value: number[];
  loading?: boolean;
  onChange: (ids: number[]) => void;
  onCancel: () => void;
  onConfirm: () => void;
}

const MAX_SELECTED = 8;

export function ProfilePicker({
  profiles,
  value,
  loading = false,
  onChange,
  onCancel,
  onConfirm,
}: ProfilePickerProps) {
  const selected = new Set(value);

  const toggle = (profileId: number) => {
    const next = new Set(value);
    if (next.has(profileId)) {
      next.delete(profileId);
    } else if (next.size < MAX_SELECTED) {
      next.add(profileId);
    }
    onChange([...next]);
  };

  return (
    <section className="profile-picker" aria-label="选择本轮人物">
      <header className="profile-picker-header">
        <strong>选择本轮人物</strong>
        <span>{value.length}/{MAX_SELECTED}</span>
      </header>

      <div className="profile-picker-list" aria-busy={loading}>
        {loading ? (
          [0, 1, 2].map((item) => <Skeleton.Input key={item} active block />)
        ) : profiles.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可选档案" />
        ) : (
          profiles.map((profile) => {
            const checked = selected.has(profile.id);
            const disabled = !checked && value.length >= MAX_SELECTED;
            return (
              <label
                key={profile.id}
                className={`profile-picker-row${checked ? " is-selected" : ""}${disabled ? " is-disabled" : ""}`}
              >
                <Checkbox
                  checked={checked}
                  disabled={disabled}
                  onChange={() => toggle(profile.id)}
                  aria-label={`${profile.name}，${profile.relationship_type}`}
                />
                <span className="profile-picker-copy">
                  <span className="profile-picker-name-line">
                    <span className="profile-name">{profile.name}</span>
                    <Tag className="profile-relation-tag">{profile.relationship_type}</Tag>
                  </span>
                  <span className="profile-picker-meta">
                    {compactBirth(profile)} · {profile.pillars?.year ? "已排盘" : "待排盘"}
                  </span>
                </span>
              </label>
            );
          })
        )}
      </div>

      <footer className="profile-picker-footer">
        <Button type="text" disabled={value.length === 0} onClick={() => onChange([])}>
          清空
        </Button>
        <span className="profile-picker-footer-actions">
          <Button onClick={onCancel}>取消</Button>
          <Button type="primary" onClick={onConfirm}>确认{value.length ? ` (${value.length})` : ""}</Button>
        </span>
      </footer>
    </section>
  );
}
