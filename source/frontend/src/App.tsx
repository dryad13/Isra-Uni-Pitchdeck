import { useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import { usePending } from "./context/PendingContext";
import OperatorDashboard from "./pages/OperatorDashboard";
import Results from "./pages/Results";
import ExportReport from "./pages/ExportReport";
import LayoutCalibrator from "./pages/LayoutCalibrator";
import AccuracyLab from "./pages/AccuracyLab";
import Roster from "./pages/Roster";
import SheetDetail from "./pages/SheetDetail";
import AdvancedTools from "./pages/AdvancedTools";
import NotFound from "./pages/NotFound";
import ExamsRedirect from "./pages/ExamsRedirect";
import logo from "./assets/logo.png";
import "./App.css";

function navClass({ isActive }: { isActive: boolean }) {
  return isActive ? "nav-link active" : "nav-link";
}

export default function App() {
  const { pending } = usePending();
  const [navOpen, setNavOpen] = useState(false);
  const closeNav = () => setNavOpen(false);

  return (
    <div className={`app-shell${navOpen ? " nav-open" : ""}`}>
      <button
        type="button"
        className="nav-backdrop"
        aria-label="Close navigation menu"
        tabIndex={navOpen ? 0 : -1}
        onClick={closeNav}
      />
      <aside className="app-sidebar">
        <Link to="/" className="brand" onClick={closeNav}>
          OMR Console
        </Link>
        <nav className="app-nav" id="app-nav">
          <NavLink to="/" className={navClass} end onClick={closeNav}>
            Run exam
          </NavLink>
          <NavLink to="/verify" className={navClass} onClick={closeNav}>
            Results
            {pending > 0 && <span className="nav-count">{pending}</span>}
          </NavLink>
          <NavLink to="/export" className={navClass} onClick={closeNav}>
            Reports
          </NavLink>
          <NavLink to="/roster" className={navClass} onClick={closeNav}>
            Roster
          </NavLink>
          <NavLink to="/advanced" className={navClass} onClick={closeNav}>
            Tools
          </NavLink>
        </nav>
      </aside>
      <div className="app-main">
        <header className="app-header">
          <button
            type="button"
            className="nav-toggle"
            aria-expanded={navOpen}
            aria-controls="app-nav"
            onClick={() => setNavOpen((open) => !open)}
          >
            <span className="nav-toggle-icon" aria-hidden="true" />
            Menu
          </button>
          <Link to="/" className="app-header-logo" aria-label="Isra University home">
            <img src={logo} alt="Isra University Hyderabad Sindh" />
          </Link>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<OperatorDashboard />} />
            <Route path="/exams" element={<ExamsRedirect />} />
            <Route path="/verify" element={<Results />} />
            <Route path="/export" element={<ExportReport />} />
            <Route path="/roster" element={<Roster />} />
            <Route path="/sheets/:sheetId" element={<SheetDetail />} />
            <Route path="/advanced" element={<AdvancedTools />} />
            <Route path="/advanced/calibrator" element={<LayoutCalibrator />} />
            <Route path="/advanced/accuracy" element={<AccuracyLab />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
