import { useCallback, useEffect, useState } from "react";

type PromptOutcome = "accepted" | "dismissed";
export type PwaInstallTarget =
  | "native"
  | "ios"
  | "android"
  | "inAppBrowser"
  | "mobile"
  | "desktop";
export type PwaInstallPromptResult = PromptOutcome | "unavailable";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: PromptOutcome; platform: string }>;
}

type LegacyMediaQueryList = MediaQueryList & {
  addListener?: (listener: () => void) => void;
  removeListener?: (listener: () => void) => void;
};

interface InstallEnvironment {
  installed: boolean;
  ios: boolean;
  android: boolean;
  mobile: boolean;
  inAppBrowser: boolean;
}

function isStandaloneDisplay(): boolean {
  const navigatorWithStandalone = navigator as Navigator & { standalone?: boolean };
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    navigatorWithStandalone.standalone === true
  );
}

function getInstallEnvironment(): InstallEnvironment {
  const userAgent = navigator.userAgent || "";
  const platform = navigator.platform || "";
  const maxTouchPoints = navigator.maxTouchPoints || 0;
  const ios =
    /iPad|iPhone|iPod/i.test(userAgent) ||
    (platform === "MacIntel" && maxTouchPoints > 1);
  const android = /Android/i.test(userAgent);
  const mobile = ios || android || /Mobile|Tablet/i.test(userAgent);
  const inAppBrowser =
    /MicroMessenger|QQ\/|WeiBo|AlipayClient|DingTalk|Lark|Feishu|BytedanceWebview|NewsArticle|FBAN|FBAV|Instagram/i.test(
      userAgent,
    );

  return {
    installed: isStandaloneDisplay(),
    ios,
    android,
    mobile,
    inAppBrowser,
  };
}

function getInstallTarget(
  environment: InstallEnvironment,
  promptEvent: BeforeInstallPromptEvent | null,
): PwaInstallTarget {
  if (promptEvent) {
    return "native";
  }
  if (environment.inAppBrowser) {
    return "inAppBrowser";
  }
  if (environment.ios) {
    return "ios";
  }
  if (environment.android) {
    return "android";
  }
  if (environment.mobile) {
    return "mobile";
  }
  return "desktop";
}

export function usePwaInstall() {
  const [promptEvent, setPromptEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [environment, setEnvironment] = useState<InstallEnvironment>(() => getInstallEnvironment());

  useEffect(() => {
    const updateEnvironment = () => setEnvironment(getInstallEnvironment());
    const handleBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setPromptEvent(event as BeforeInstallPromptEvent);
      updateEnvironment();
    };
    const handleInstalled = () => {
      setPromptEvent(null);
      updateEnvironment();
    };

    updateEnvironment();
    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleInstalled);

    const displayModeQuery = window.matchMedia("(display-mode: standalone)");
    const legacyDisplayModeQuery = displayModeQuery as LegacyMediaQueryList;
    if (typeof displayModeQuery.addEventListener === "function") {
      displayModeQuery.addEventListener("change", updateEnvironment);
    } else {
      legacyDisplayModeQuery.addListener?.(updateEnvironment);
    }

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleInstalled);
      if (typeof displayModeQuery.removeEventListener === "function") {
        displayModeQuery.removeEventListener("change", updateEnvironment);
      } else {
        legacyDisplayModeQuery.removeListener?.(updateEnvironment);
      }
    };
  }, []);

  const promptInstall = useCallback(async (): Promise<PwaInstallPromptResult> => {
    if (!promptEvent) {
      return "unavailable";
    }
    await promptEvent.prompt();
    const choice = await promptEvent.userChoice;
    setPromptEvent(null);
    setEnvironment((prev) => ({
      ...prev,
      installed: choice.outcome === "accepted" || isStandaloneDisplay(),
    }));
    return choice.outcome;
  }, [promptEvent]);

  const installTarget = getInstallTarget(environment, promptEvent);
  const canInstall = !environment.installed && (Boolean(promptEvent) || environment.mobile);

  return {
    canInstall,
    canPromptInstall: Boolean(promptEvent) && !environment.installed,
    installed: environment.installed,
    installTarget,
    promptInstall,
  };
}
