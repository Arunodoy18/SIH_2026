import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { NirnayProvider } from "./store";
import { Landing } from "./pages/Landing";
import { Districts } from "./pages/Districts";
import { Overview } from "./pages/Overview";
import { HabitationPage } from "./pages/HabitationPage";
import { PlanPage } from "./pages/PlanPage";

export function App() {
  return (
    <NirnayProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/districts" element={<Districts />} />
          <Route path="/districts/mangan" element={<Overview />} />
          <Route path="/districts/mangan/habitations/:habId" element={<HabitationPage />} />
          <Route path="/districts/mangan/plan" element={<PlanPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </NirnayProvider>
  );
}
