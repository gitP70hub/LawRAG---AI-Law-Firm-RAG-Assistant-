import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage     from './pages/LandingPage';
import Dashboard       from './pages/Dashboard';
import LawyerDashboard from './pages/LawyerDashboard';
import CaseDetail      from './pages/CaseDetail';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"            element={<LandingPage />} />
        <Route path="/dashboard"   element={<Dashboard />} />
        <Route path="/lawyer"      element={<LawyerDashboard />} />
        <Route path="/case/:id"    element={<CaseDetail />} />
        <Route path="*"            element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
