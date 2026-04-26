import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ClientDashboard from './pages/ClientDashboard';
import LawyerDashboard from './pages/LawyerDashboard';
import CaseDetail      from './pages/CaseDetail';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"          element={<ClientDashboard />} />
        <Route path="/lawyer"    element={<LawyerDashboard />} />
        <Route path="/case/:id"  element={<CaseDetail />} />
        <Route path="*"          element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
