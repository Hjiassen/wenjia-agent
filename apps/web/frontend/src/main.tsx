import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App as AntdApp, ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import { registerServiceWorker } from "./lib/serviceWorker";
import { theme } from "./theme";
import "./styles.css";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root container #root not found.");
}

createRoot(container).render(
  <StrictMode>
    <ConfigProvider locale={zhCN} theme={theme}>
      <AntdApp>
        <App />
      </AntdApp>
    </ConfigProvider>
  </StrictMode>,
);

registerServiceWorker();
