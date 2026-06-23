import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import "./fixedPdfGuard";
import "./reviewGuard";
import "./signOutFix";
import "./mlModelPageCleanup";
import "./predictGuard";
import "./applyReviewNotificationGuard";
import "./applyWorkflowHideGuard";
import "./applyReviewHistoryScrollFix";
import "./applyBottomSectionsHideGuard";
import "./applyUpdateApplicationTitleGuard";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
