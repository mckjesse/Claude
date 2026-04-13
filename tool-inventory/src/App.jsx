import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Tools from './pages/Tools';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import MovementHistory from './pages/MovementHistory';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/tools" element={<Tools />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/history" element={<MovementHistory />} />
      </Route>
    </Routes>
  );
}
