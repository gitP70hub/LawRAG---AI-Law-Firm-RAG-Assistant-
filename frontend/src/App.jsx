import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage      from './pages/LandingPage';
import Dashboard        from './pages/Dashboard';
import ClientDashboard  from './pages/ClientDashboard';
import LawyerDashboard  from './pages/LawyerDashboard';
import CaseDetail       from './pages/CaseDetail';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Landing */}
        <Route path="/"            element={<LandingPage />} />

        {/* Main lawyer/admin dashboard */}
        <Route path="/dashboard"   element={<Dashboard />} />

        {/* Role-specific dashboards */}
        <Route path="/client"      element={<ClientDashboard />} />
        <Route path="/lawyer"      element={<LawyerDashboard />} />

        {/* Case detail */}
        <Route path="/case/:id"    element={<CaseDetail />} />

        {/* Fallback */}
        <Route path="*"            element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
