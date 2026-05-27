import { HashRouter, Routes, Route } from "react-router-dom";
import { ErrorBoundary } from "./components/primitives/error-boundary";
import Layout from "./sections/Layout";
import ProspectSetup from "./sections/ProspectSetup";
import ProspectIntelligence from "./sections/ProspectIntelligence";
import AIGeneratedModel from "./sections/AIGeneratedModel";
import ValueDriverTree from "./sections/ValueDriverTree";
import EvidenceMatch from "./sections/EvidenceMatch";
import ValueCalculator from "./sections/ValueCalculator";
import GeneratedValueCase from "./sections/GeneratedValueCase";
import SetupScreen from "./settings/SetupScreen";
import SettingsScreen from "./settings/SettingsScreen";
import OperationsScreen from "./settings/OperationsScreen";
import NotFound from "./pages/NotFound";
import ValueStudioExplorer from "./pages/ValueStudioExplorer";
import AgentMockup from "./pages/AgentMockup";

export default function App() {
  return (
    <HashRouter>
      <ErrorBoundary>
        <Routes>
          <Route element={<Layout />}>
            {/* Workflow */}
            <Route index element={<ProspectSetup />} />
            <Route path="intelligence" element={<ProspectIntelligence />} />
            <Route path="ai-model" element={<AIGeneratedModel />} />
            <Route path="driver-tree" element={<ValueDriverTree />} />
            <Route path="evidence" element={<EvidenceMatch />} />
            <Route path="calculator" element={<ValueCalculator />} />
            <Route path="value-case" element={<GeneratedValueCase />} />
            {/* Setup */}
            <Route path="setup" element={<SetupScreen />} />
            {/* Settings */}
            <Route path="settings" element={<SettingsScreen />} />
            {/* Operations */}
            <Route path="operations" element={<OperationsScreen />} />
            {/* 404 */}
            <Route path="*" element={<NotFound />} />
          </Route>
          {/* Value Studio — full-screen, own layout */}
          <Route path="studio" element={<ValueStudioExplorer />} />
          {/* Agentic AI Co-Pilot Mockup */}
          <Route path="agent" element={<AgentMockup />} />
        </Routes>
      </ErrorBoundary>
    </HashRouter>
  );
}
