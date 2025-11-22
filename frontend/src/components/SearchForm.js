import React, { useState } from 'react';
import './SearchForm.css';

function SearchForm({ onSearch, loading }) {
  const [url, setUrl] = useState('');
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim() && query.trim() && !loading) {
      onSearch(url.trim(), query.trim());
    }
  };

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <div className="form-row">
        <div className="input-group">
          <span className="input-icon">🌐</span>
          <input
            type="url"
            id="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            required
            disabled={loading}
            className="form-input"
          />
        </div>

        <div className="input-group">
          <span className="input-icon">🔍</span>
          <input
            type="text"
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your search query..."
            required
            disabled={loading}
            className="form-input"
          />
        </div>

        <button
          type="submit"
          className="search-button"
          disabled={loading || !url.trim() || !query.trim()}
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>
    </form>
  );
}

export default SearchForm;
