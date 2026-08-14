import { useCallback, useEffect, useMemo, useState } from "react";
import {
  App as AntdApp,
  Badge,
  Button,
  Dropdown,
  Empty,
  Input,
  Popconfirm,
  Skeleton,
  Tabs,
  Tag,
  Tooltip,
} from "antd";
import {
  ArrowLeftOutlined,
  CopyOutlined,
  CloseOutlined,
  DeleteOutlined,
  EditOutlined,
  MoreOutlined,
  PlusOutlined,
  UndoOutlined,
  UserOutlined,
} from "@ant-design/icons";
import type { Profile, ProfileCandidate } from "../types";
import { compactBirth, compactPillars } from "../lib/profileText";
import { ProfileEditor } from "./ProfileEditor";

type ProfileTab = "profiles" | "candidates" | "deleted";
type EditorState = {
  profile?: Profile;
  candidate?: ProfileCandidate;
  relationship?: string;
  returnToChat?: boolean;
} | null;

interface ProfileManagerProps {
  profiles: Profile[];
  onBack: () => void;
  onProfilesChanged: () => void | Promise<void>;
  onCandidateCountChange?: (count: number) => void;
  initialTab?: ProfileTab;
  initialCreateRelationship?: string | null;
  onProfileSaved?: (profile: Profile) => void;
  onInitialCreateCancelled?: () => void;
}

function profileText(profile: Profile): string {
  const relationship = profile.relationship_type === "其他" && profile.custom_relationship
    ? `其他（${profile.custom_relationship}）`
    : profile.relationship_type;
  const birth = profile.birth;
  const birthDate = birth?.year && birth.month && birth.day
    ? `${birth.year}年${birth.month}月${birth.day}日`
    : "未填写";
  const birthTime = birth?.hour !== null && birth?.hour !== undefined
    ? `${String(birth.hour).padStart(2, "0")}:${String(birth.minute ?? 0).padStart(2, "0")}`
    : "未填写";
  const calendar = birth?.calendar_type === "solar"
    ? "公历"
    : birth?.calendar_type === "lunar"
      ? `农历${birth.is_leap_month ? "（闰月）" : ""}`
      : "未填写";
  const locationParts = [birth?.province, birth?.city].filter(
    (value, index, values) => value && values.indexOf(value) === index,
  );
  const elements = profile.five_elements
    ? Object.entries(profile.five_elements).map(([key, value]) => `${key}${value}`).join("、")
    : "未填写";
  return [
    `姓名：${profile.name}`,
    `与本人关系：${relationship}`,
    `性别：${profile.gender || "未填写"}`,
    `出生日期：${birthDate}`,
    `出生时间：${birthTime}`,
    `历法：${calendar}`,
    `出生地：${locationParts.length ? locationParts.join(" ") : "未填写"}`,
    `四柱：${compactPillars(profile) || "未填写"}`,
    `五行：${elements}`,
    `档案状态：${profile.pillars?.year ? "已排盘" : "待排盘"}`,
  ].join("\n");
}

export function ProfileManager({
  profiles,
  onBack,
  onProfilesChanged,
  onCandidateCountChange,
  initialTab = "profiles",
  initialCreateRelationship = null,
  onProfileSaved,
  onInitialCreateCancelled,
}: ProfileManagerProps) {
  const { message, modal } = AntdApp.useApp();
  const [tab, setTab] = useState<ProfileTab>(initialTab);
  const [editor, setEditor] = useState<EditorState>(
    initialCreateRelationship
      ? { relationship: initialCreateRelationship, returnToChat: true }
      : null,
  );
  const [candidates, setCandidates] = useState<ProfileCandidate[]>([]);
  const [deleted, setDeleted] = useState<Profile[]>([]);
  const [loadingAuxiliary, setLoadingAuxiliary] = useState(true);
  const selfProfile = useMemo(
    () => profiles.find((profile) => profile.relationship_type === "本人"),
    [profiles],
  );

  const loadAuxiliary = useCallback(async () => {
    setLoadingAuxiliary(true);
    try {
      const [candidateResponse, deletedResponse] = await Promise.all([
        fetch("/api/profile-candidates", { credentials: "include" }),
        fetch("/api/profiles/deleted", { credentials: "include" }),
      ]);
      const candidatePayload = await candidateResponse.json().catch(() => null);
      const deletedPayload = await deletedResponse.json().catch(() => null);
      const nextCandidates = Array.isArray(candidatePayload?.candidates) ? candidatePayload.candidates : [];
      setCandidates(nextCandidates);
      setDeleted(Array.isArray(deletedPayload?.profiles) ? deletedPayload.profiles : []);
      onCandidateCountChange?.(nextCandidates.length);
    } finally {
      setLoadingAuxiliary(false);
    }
  }, [onCandidateCountChange]);

  useEffect(() => { void loadAuxiliary(); }, [loadAuxiliary]);

  const handleSaved = async (profile: Profile) => {
    setEditor(null);
    await onProfilesChanged();
    await loadAuxiliary();
    onProfileSaved?.(profile);
  };

  const handleDelete = (profile: Profile) => {
    modal.confirm({
      title: `将“${profile.name}”移入回收站？`,
      content: "历史对话仍保留当时的档案名称，但后续不会再使用该档案。",
      okText: "移入回收站",
      cancelText: "取消",
      okButtonProps: { danger: true },
      async onOk() {
        const response = await fetch(`/api/profiles/${profile.id}`, {
          method: "DELETE",
          credentials: "include",
        });
        if (!response.ok) {
          message.error("档案删除失败");
          throw new Error("profile delete failed");
        }
        message.success("档案已移入回收站");
        await onProfilesChanged();
        await loadAuxiliary();
      },
    });
  };

  const handleRestore = async (profile: Profile) => {
    const response = await fetch(`/api/profiles/${profile.id}/restore`, {
      method: "POST",
      credentials: "include",
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      message.error(payload?.detail || "档案恢复失败");
      return;
    }
    message.success("档案已恢复");
    await onProfilesChanged();
    await loadAuxiliary();
  };

  const dismissCandidate = async (candidate: ProfileCandidate) => {
    const response = await fetch(`/api/profile-candidates/${candidate.id}/dismiss`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      message.error("忽略候选人物失败");
      return;
    }
    message.success("已忽略候选人物");
    await loadAuxiliary();
  };

  const copyProfile = async (profile: Profile) => {
    try {
      await navigator.clipboard.writeText(profileText(profile));
      message.success("档案文本已复制");
    } catch {
      modal.info({
        title: "复制档案文本",
        okText: "关闭",
        content: (
          <Input.TextArea
            readOnly
            autoFocus
            autoSize={{ minRows: 8, maxRows: 14 }}
            value={profileText(profile)}
            onFocus={(event) => event.currentTarget.select()}
          />
        ),
      });
    }
  };

  if (editor) {
    return (
      <ProfileEditor
        profile={editor.profile}
        candidate={editor.candidate}
        initialRelationship={editor.relationship}
        onCancel={() => {
          const returnsToChat = editor.returnToChat;
          setEditor(null);
          if (returnsToChat) onInitialCreateCancelled?.();
        }}
        onSaved={(profile) => void handleSaved(profile)}
      />
    );
  }

  const profileList = profiles.length === 0 ? (
    <Empty description="还没有人物档案">
      <Button
        type="primary"
        icon={<PlusOutlined />}
        className="profile-empty-create"
        aria-label="新增人物"
        title="新增人物"
        onClick={() => setEditor({ relationship: "本人" })}
      >
        <span className="profile-button-label">新增人物</span>
      </Button>
    </Empty>
  ) : (
    <div className="profile-management-list" role="list">
      {profiles.map((profile) => (
        <article key={profile.id} className="profile-management-row" role="listitem">
          <span className="profile-management-avatar" aria-hidden="true"><UserOutlined /></span>
          <div className="profile-management-main">
            <div className="profile-management-title">
              <strong>{profile.name}</strong>
              <Tag className="profile-relation-tag">{profile.relationship_type}</Tag>
            </div>
            <span className="profile-management-meta">{compactBirth(profile)}</span>
          </div>
          <span className={`profile-status${profile.pillars?.year ? " is-ready" : ""}`}>
            {profile.pillars?.year ? "已排盘" : "待完善"}
          </span>
          <div className="profile-management-actions">
            <Tooltip title="复制档案文本">
              <Button type="text" icon={<CopyOutlined />} aria-label={`复制${profile.name}的档案文本`} onClick={() => void copyProfile(profile)} />
            </Tooltip>
            <Tooltip title="编辑人物档案">
              <Button type="text" icon={<EditOutlined />} aria-label={`编辑${profile.name}`} onClick={() => setEditor({ profile })} />
            </Tooltip>
            <Dropdown
              trigger={["click"]}
              menu={{
                items: [{ key: "delete", danger: true, icon: <DeleteOutlined />, label: "移入回收站" }],
                onClick: () => handleDelete(profile),
              }}
            >
              <Button type="text" icon={<MoreOutlined />} aria-label={`${profile.name}的更多操作`} />
            </Dropdown>
          </div>
        </article>
      ))}
    </div>
  );

  const candidateList = loadingAuxiliary ? <Skeleton active /> : candidates.length === 0 ? (
    <Empty description="暂无待补充人物" />
  ) : (
    <div className="profile-management-list" role="list">
      {candidates.map((candidate) => (
        <article key={candidate.id} className="profile-management-row candidate-row" role="listitem">
          <span className="profile-management-avatar is-pending" aria-hidden="true"><UserOutlined /></span>
          <div className="profile-management-main">
            <div className="profile-management-title">
              <strong>{candidate.display_name}</strong>
              {candidate.suggested_relationship ? <Tag className="candidate-relation-tag">建议：{candidate.suggested_relationship}</Tag> : null}
            </div>
            <span className="profile-management-meta">尚未保存为正式档案</span>
          </div>
          <div className="candidate-actions">
            <Tooltip title="补充资料">
              <Button
                type="primary"
                size="small"
                icon={<EditOutlined />}
                className="candidate-action-button"
                aria-label={`补充${candidate.display_name}的资料`}
                onClick={() => setEditor({ candidate })}
              >
                <span className="profile-button-label">补充资料</span>
              </Button>
            </Tooltip>
            <Popconfirm title="忽略这位候选人物？" okText="忽略" cancelText="取消" onConfirm={() => void dismissCandidate(candidate)}>
              <Tooltip title="忽略候选人物">
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined />}
                  className="candidate-action-button"
                  aria-label={`忽略${candidate.display_name}`}
                >
                  <span className="profile-button-label">忽略</span>
                </Button>
              </Tooltip>
            </Popconfirm>
          </div>
        </article>
      ))}
    </div>
  );

  const deletedList = loadingAuxiliary ? <Skeleton active /> : deleted.length === 0 ? (
    <Empty description="回收站为空" />
  ) : (
    <div className="profile-management-list" role="list">
      {deleted.map((profile) => (
        <article key={profile.id} className="profile-management-row" role="listitem">
          <span className="profile-management-avatar is-muted" aria-hidden="true"><UserOutlined /></span>
          <div className="profile-management-main">
            <div className="profile-management-title"><strong>{profile.name}</strong><Tag className="profile-relation-tag">{profile.relationship_type}</Tag></div>
            <span className="profile-management-meta">已移入回收站</span>
          </div>
          <Tooltip title="恢复人物档案">
            <Button
              icon={<UndoOutlined />}
              className="profile-restore-button"
              aria-label={`恢复${profile.name}`}
              onClick={() => void handleRestore(profile)}
            >
              <span className="profile-button-label">恢复</span>
            </Button>
          </Tooltip>
        </article>
      ))}
    </div>
  );

  return (
    <section className="profile-management-page">
      <header className="profile-module-header">
        <Button type="text" icon={<ArrowLeftOutlined />} aria-label="返回对话" onClick={onBack} />
        <div className="profile-module-title"><h1>人物档案</h1><p>维护本人及相关人物的出生资料</p></div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          className="profile-header-create"
          aria-label="新增人物"
          onClick={() => setEditor({ relationship: selfProfile ? "朋友" : "本人" })}
        >
          <span className="profile-button-label">新增人物</span>
        </Button>
      </header>

      <div className="profile-management-scroll">
        <div className="profile-management-content">
          {!selfProfile ? (
            <section className="profile-self-callout">
              <div><strong>还没有本人档案</strong><p>创建后可在提问时直接选择，无需重复填写出生资料。</p></div>
              <Tooltip title="创建本人档案">
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  className="profile-self-create"
                  aria-label="创建本人档案"
                  onClick={() => setEditor({ relationship: "本人" })}
                >
                  <span className="profile-button-label">表单填写</span>
                </Button>
              </Tooltip>
            </section>
          ) : null}

          <section className="profile-overview" aria-label="人物档案概览">
            <div><span>本人档案</span><strong>{selfProfile ? "已建立" : "未建立"}</strong></div>
            <div><span>有效档案</span><strong>{profiles.length}</strong></div>
            <div><span>待补充</span><strong>{candidates.length}</strong></div>
          </section>

          <Tabs
            activeKey={tab}
            onChange={(key) => setTab(key as ProfileTab)}
            items={[
              { key: "profiles", label: "我的档案", children: profileList },
              { key: "candidates", label: <span>待补充 {candidates.length ? <Badge count={candidates.length} size="small" /> : null}</span>, children: candidateList },
              { key: "deleted", label: "回收站", children: deletedList },
            ]}
          />
        </div>
      </div>
    </section>
  );
}
