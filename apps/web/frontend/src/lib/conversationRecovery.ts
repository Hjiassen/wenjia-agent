export function shouldRefreshConversationOnResume(
  visibilityState: string,
  isSending: boolean,
): boolean {
  return visibilityState === "visible" && !isSending;
}
