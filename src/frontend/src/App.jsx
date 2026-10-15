import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import Overview from './pages/Overview.jsx';
import Records from './pages/Records.jsx';
import Schedule from './pages/Schedule.jsx';
import Backups from './pages/Backups.jsx';
import Forecast from './pages/Forecast.jsx';
import System from './pages/System.jsx';
import StorageRetrieval from './pages/StorageRetrieval.jsx';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="storage-retrieval" element={<StorageRetrieval />} />
        <Route path="records" element={<Records />} />
        <Route path="schedule" element={<Schedule />} />
        <Route path="backups" element={<Backups />} />
        <Route path="forecast" element={<Forecast />} />
        <Route path="system" element={<System />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
