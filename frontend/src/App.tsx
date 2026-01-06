import { Routes, Route } from 'react-router-dom'
import Header from './components/common/Header'
import Sidebar from './components/common/Sidebar'
import HomePage from './pages/HomePage'
import StatePage from './pages/StatePage'
import PoliticianPage from './pages/PoliticianPage'
import AboutPage from './pages/AboutPage'
import SearchPage from './pages/SearchPage'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/state/:stateCode" element={<StatePage />} />
            <Route path="/politician/:id" element={<PoliticianPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/search" element={<SearchPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
