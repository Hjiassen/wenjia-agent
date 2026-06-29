// Guidance prompts shown as chips in the chat area to kickstart a conversation.
export interface RecommendedPrompt {
  label: string;
  prompt: string;
}

export const RECOMMENDED_PROMPTS: RecommendedPrompt[] = [
  {
    label: "事业趋势需要哪些资料",
    prompt: "我最近事业怎么样？需要我先补充哪些出生信息？",
  },
  {
    label: "快速排一个基础命盘",
    prompt:
      "请排基础命盘：姓名测试，性别未知，公历1995年5月12日9点30分，出生地北京市北京市。只输出四柱和五行分布。",
  },
  {
    label: "继续追问职业方向",
    prompt: "基于刚才的出生信息，请用稳健、非绝对化的方式分析适合的职业方向。",
  },
  {
    label: "起名前需要准备什么",
    prompt: "我想给一个孩子起名，请先告诉我需要提供哪些出生信息和偏好信息。",
  },
];
