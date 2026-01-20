import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";
import "./index.css";
import App from "./App.jsx";
import { ThemeProvider } from "./lib/theme.jsx";
import { WalletProvider } from "./lib/WalletProvider.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ThemeProvider>
      <WalletProvider>
        <BrowserRouter>
        <App />
        <Toaster position="top-right" richColors />
      </BrowserRouter>
      </WalletProvider>
    </ThemeProvider>
  </StrictMode>
);
