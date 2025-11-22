import React, { useState } from 'react';
import './App.css';
import SearchForm from './components/SearchForm';
import ResultsDisplay from './components/ResultsDisplay';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [url, setUrl] = useState('');
  const [query, setQuery] = useState('');

  const handleSearch = async (searchUrl, searchQuery) => {
    setLoading(true);
    setError(null);
    setResults([]);
    setUrl(searchUrl);
    setQuery(searchQuery);

    try {
      let fetchResponse;
      try {
        fetchResponse = await fetch(`${API_BASE_URL}/api/fetch/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ url: searchUrl }),
        });
      } catch (networkError) {
        if (networkError instanceof TypeError && networkError.message.includes('fetch')) {
          throw new Error('Backend server is not running. Please check the API URL configuration.');
        }
        throw networkError;
      }

      if (!fetchResponse.ok) {
        let errorData;
        try {
          errorData = await fetchResponse.json();
        } catch {
          errorData = { error: `Server error: ${fetchResponse.status} ${fetchResponse.statusText}` };
        }
        throw new Error(errorData.error || 'Failed to fetch URL');
      }

      let searchResponse;
      try {
        searchResponse = await fetch(`${API_BASE_URL}/api/search/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query: searchQuery, url: searchUrl }),
        });
      } catch (networkError) {
        if (networkError instanceof TypeError && networkError.message.includes('fetch')) {
          throw new Error('Backend server is not running. Please check the API URL configuration.');
        }
        throw networkError;
      }

      if (!searchResponse.ok) {
        let errorData;
        try {
          errorData = await searchResponse.json();
        } catch {
          errorData = { error: `Server error: ${searchResponse.status} ${searchResponse.statusText}` };
        }
        throw new Error(errorData.error || 'Search failed');
      }

      const searchData = await searchResponse.json();
      setResults(searchData.results || []);
    } catch (err) {
      setError(err.message || 'An unexpected error occurred. Please check if the backend server is running.');
      console.error('Error:', err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <h1>Website Content Search</h1>
          <p className="subtitle">Search through website content with precision</p>
        </header>

        <SearchForm onSearch={handleSearch} loading={loading} />

        {error && (
          <div className="error-message">
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Processing your request...</p>
          </div>
        )}

        {results.length > 0 && (
          <ResultsDisplay results={results} url={url} query={query} />
        )}
      </div>
    </div>
  );
}

export default App;
