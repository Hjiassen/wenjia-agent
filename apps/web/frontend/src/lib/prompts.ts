// Guidance prompts shown as chips in the chat area to kickstart a conversation.
export interface RecommendedPrompt {
  label: string;
  description: string;
  prompt: string;
}

export const RECOMMENDED_PROMPTS: RecommendedPrompt[] = [
  {
    label: "先补齐出生信息",
    description: "按步骤补全生日、时辰和出生地。",
    prompt: "我想做一次命理分析，请先按步骤问我需要补充哪些出生信息，不要直接开始推演。",
  },
  {
    label: "建立人物档案",
    description: "快速创建档案，后续提问可直接附加。",
    prompt: "请引导我创建一个人物档案，告诉我需要提供哪些信息，并按最少步骤让我补全。",
  },
  {
    label: "选择分析方向",
    description: "还没想好问题，先看可分析方向。",
    prompt: "我还不确定要问什么，请先给我几个可选分析方向，并说明每个方向需要哪些资料。",
  },
  {
    label: "起名前准备清单",
    description: "准备姓氏、偏好、避讳和出生信息。",
    prompt: "如果要做起名分析，请先列出需要准备的信息，并逐项引导我填写。",
  },
];
