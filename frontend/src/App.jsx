import HomePage from './pages/HomePage.jsx';

function App() {
  return (
    <main>
      <header className="app-header">
        <p className="eyebrow">Explore your data</p>
        <h1>AI-Powered Data Analysis</h1>
        <p>Upload a dataset to get started with your analysis.</p>
      </header>
      <HomePage />
    </main>
  );
}

export default App;