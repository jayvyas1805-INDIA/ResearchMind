import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Upload from "./pages/Upload.jsx";
import PaperDetail from "./pages/PaperDetail.jsx";
import Search from "./pages/Search.jsx";
import Chat from "./pages/Chat.jsx";
import Summary from "./pages/Summary.jsx";
import Compare from "./pages/Compare.jsx";
import Papers from "./pages/Papers.jsx";
import Settings from "./pages/Settings.jsx";
import Leaderboard from "./pages/Leaderboard.jsx";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/search" element={<Search />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/papers/:paperId/summary" element={<Summary />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/papers" element={<Papers />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/papers/:paperId" element={<PaperDetail />} />
        </Routes>
      </main>
    </div>
  );
}
