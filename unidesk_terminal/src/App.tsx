import { Route, HashRouter, Routes } from "react-router-dom";
import { ModeProvider } from "./lib/ModeContext";
import { Candidates } from "./screens/Candidates";
import { History } from "./screens/History";
import { Research } from "./screens/Research";
import { Settings } from "./screens/Settings";
import { Stock } from "./screens/Stock";
import { Tonight } from "./screens/Tonight";

export default function App() {
  return (
    <ModeProvider>
      <HashRouter>
        <Routes>
          <Route path="/" element={<Tonight />} />
          <Route path="/candidates" element={<Candidates />} />
          <Route path="/stock" element={<Stock />} />
          <Route path="/stock/:symbol" element={<Stock />} />
          <Route path="/history" element={<History />} />
          <Route path="/research" element={<Research />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </HashRouter>
    </ModeProvider>
  );
}
