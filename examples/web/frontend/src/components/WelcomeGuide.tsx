import { RECOMMENDED_PROMPTS } from "../lib/prompts";

interface WelcomeGuideProps {
  onPickPrompt: (prompt: string) => void;
}

interface Feature {
  icon: string;
  title: string;
  desc: string;
}

const FEATURES: Feature[] = [
  {
    icon: "🧭",
    title: "出生信息门禁",
    desc: "命理问题前先确认完整出生信息，缺啥问啥，不猜测。",
  },
  {
    icon: "🗓️",
    title: "确定性排盘",
    desc: "真太阳时四柱、五行、十神、纳音、神煞，全部由本地工具计算。",
  },
  {
    icon: "🔮",
    title: "命格分析",
    desc: "事业、财富、感情、健康提醒，稳健克制、不绝对化。",
  },
  {
    icon: "💞",
    title: "关系合盘",
    desc: "两人或多人相处模式与沟通建议。",
  },
  {
    icon: "✍️",
    title: "起名建议",
    desc: "可选填父母八字增强五行补益，给出可筛选的中文名清单。",
  },
  {
    icon: "🗂️",
    title: "人物档案",
    desc: "排盘后自动存档本人/父母，多轮对话与起名自动复用。",
  },
];

export function WelcomeGuide({ onPickPrompt }: WelcomeGuideProps) {
  return (
    <section className="welcome-guide" aria-label="功能介绍">
      <div className="welcome-intro">
        <h3>我能帮你做这些</h3>
        <p>
          问甲是一个八字智能体：本地确定性排盘 + 多智能体协作。点右上角
          <strong>「查看运行流」</strong>可回看整段对话的卡片推演过程。
        </p>
      </div>

      <div className="feature-grid">
        {FEATURES.map((feature) => (
          <article className="feature-card" key={feature.title}>
            <span className="feature-icon" aria-hidden>
              {feature.icon}
            </span>
            <div>
              <h4>{feature.title}</h4>
              <p>{feature.desc}</p>
            </div>
          </article>
        ))}
      </div>

      <div className="welcome-prompts">
        <p className="welcome-prompts-label">试试这些问题</p>
        <div className="prompt-chips">
          {RECOMMENDED_PROMPTS.map((item) => (
            <button
              key={item.label}
              type="button"
              className="prompt-chip"
              onClick={() => onPickPrompt(item.prompt)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
