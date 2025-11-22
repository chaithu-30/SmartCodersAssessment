import React, { useState } from 'react';
import './ResultsDisplay.css';

function ResultsDisplay({ results, url, query }) {
  const [expandedHtml, setExpandedHtml] = useState({});
  const [expandedText, setExpandedText] = useState({});

  const toggleHtml = (index) => {
    setExpandedHtml(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const toggleText = (index) => {
    setExpandedText(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const extractTitle = (text) => {
    const lines = text.split('\n').filter(line => line.trim());
    if (lines.length > 0) {
      const firstLine = lines[0].trim();
      if (firstLine.length > 100) {
        return firstLine.substring(0, 100) + '...';
      }
      return firstLine;
    }
    return text.substring(0, 100) + (text.length > 100 ? '...' : '');
  };

  const extractPath = (url) => {
    try {
      const urlObj = new URL(url);
      return urlObj.pathname || '/home';
    } catch {
      return '/home';
    }
  };

  const escapeHtml = (text) => {
    if (!text) return '';
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
  };

  const highlightKeywordsInCode = (code, searchQuery) => {
    if (!code || !searchQuery) return escapeHtml(code);
    
    const queryWords = searchQuery.toLowerCase().trim().split(/\s+/).filter(w => w.length > 2);
    if (queryWords.length === 0) return escapeHtml(code);
    
    // First escape the HTML
    let escaped = escapeHtml(code);
    
    // Find and highlight keywords (simple approach - highlight in escaped string)
    queryWords.forEach(word => {
      // Create regex for the word (case-insensitive)
      const regex = new RegExp(`(${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      
      // Replace matches with highlighted version
      escaped = escaped.replace(regex, (match) => {
        // Check if we're inside an HTML entity or tag by looking at context
        // This is a simplified check - we'll highlight anyway for code display
        return `<mark class="keyword-highlight">${match}</mark>`;
      });
    });
    
    return escaped;
  };

  const highlightKeywordsInText = (text, searchQuery) => {
    if (!text || !searchQuery) return escapeHtml(text);
    
    const queryWords = searchQuery.toLowerCase().trim().split(/\s+/).filter(w => w.length > 2);
    if (queryWords.length === 0) return escapeHtml(text);
    
    // First escape the HTML
    let escaped = escapeHtml(text);
    
    // Find and highlight keywords
    queryWords.forEach(word => {
      // Create regex for the word (case-insensitive, whole word)
      const regex = new RegExp(`\\b(${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})\\b`, 'gi');
      
      // Replace matches with highlighted version
      escaped = escaped.replace(regex, (match) => {
        return `<mark class="text-highlight">${match}</mark>`;
      });
    });
    
    return escaped;
  };

  const getTextPreview = (chunkText, matchingText, maxLength = 300) => {
    if (!chunkText) return '';
    
    // If we have matching text segments, use those
    if (matchingText && matchingText.length > 0) {
      // Combine matching segments
      const segments = matchingText
        .map(m => m.text || '')
        .filter(t => t.trim().length > 0)
        .slice(0, 3); // Limit to first 3 segments
      
      if (segments.length > 0) {
        return segments.join(' ... ');
      }
    }
    
    // Otherwise, use the first part of chunk_text
    if (chunkText.length <= maxLength) {
      return chunkText;
    }
    
    // Try to break at sentence boundary
    const truncated = chunkText.substring(0, maxLength);
    const lastPeriod = truncated.lastIndexOf('.');
    const lastExclamation = truncated.lastIndexOf('!');
    const lastQuestion = truncated.lastIndexOf('?');
    const lastBreak = Math.max(lastPeriod, lastExclamation, lastQuestion);
    
    if (lastBreak > maxLength * 0.5) {
      return truncated.substring(0, lastBreak + 1);
    }
    
    return truncated + '...';
  };

  const formatHtmlForDisplay = (htmlText, searchQuery) => {
    if (!htmlText) return '';
    
    // If it's already HTML, format it nicely for display
    if (htmlText.includes('<') && htmlText.includes('>')) {
      // Try to format/indent the HTML for better readability
      return formatHtmlCode(htmlText);
    }
    
    // Otherwise format plain text as HTML
    const lines = htmlText.split('. ');
    const htmlLines = lines.map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) return '';
      if (idx === 0 && trimmed.length > 50) {
        return `    <h1>${trimmed}</h1>`;
      }
      return `    <p>${trimmed}</p>`;
    }).filter(line => line);
    
    if (htmlLines.length === 0) {
      htmlLines.push(`    <p>${htmlText}</p>`);
    }
    
    return `<div class="content">\n${htmlLines.join('\n')}\n</div>`;
  };

  const formatHtmlCode = (html) => {
    if (!html) return '';
    
    // Remove excessive whitespace but preserve structure
    let formatted = html.trim();
    
    // Add newlines for better readability
    // Add newline after closing tags
    formatted = formatted.replace(/(<\/[^>]+>)(?=\S)/g, '$1\n');
    
    // Add newline before opening block-level tags (if not already there)
    formatted = formatted.replace(/(?<=\S)(<)(div|p|h1|h2|h3|h4|h5|h6|section|article|ul|ol|li|table|tr|td|th)/gi, '\n$1$2');
    
    // Clean up multiple newlines
    formatted = formatted.replace(/\n{3,}/g, '\n\n');
    
    // Add basic indentation
    const lines = formatted.split('\n');
    let indent = 0;
    const indentSize = 2;
    const formattedLines = [];
    
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        formattedLines.push('');
        continue;
      }
      
      // Decrease indent for closing tags
      if (trimmed.startsWith('</')) {
        indent = Math.max(0, indent - indentSize);
      }
      
      // Add line with current indent
      formattedLines.push(' '.repeat(indent) + trimmed);
      
      // Increase indent for opening tags (except self-closing and inline elements)
      if (trimmed.startsWith('<') && !trimmed.endsWith('/>') && 
          !trimmed.match(/^<(img|br|hr|input|meta|link|area|base|col|embed|source|track|wbr|span|a|strong|em|b|i|u|code|small)/i) &&
          !trimmed.startsWith('</')) {
        indent += indentSize;
      }
    }
    
    return formattedLines.join('\n');
  };

  return (
    <div className="results-display">
      <div className="results-header">
        <h2>Search Results</h2>
      </div>

      <div className="results-list">
        {results.map((result, index) => {
          const title = extractTitle(result.chunk_text);
          const path = extractPath(result.url);
          const matchPercent = Math.round(result.relevance_score * 100);
          const isHtmlExpanded = expandedHtml[index];
          const isTextExpanded = expandedText[index];
          const htmlContent = formatHtmlForDisplay(result.chunk_html || result.chunk_text, query);
          const textPreview = getTextPreview(result.chunk_text, result.matching_text);
          const fullText = result.chunk_text || '';

          return (
            <div key={index} className="result-card">
              <div className="result-title-row">
                <div className="result-title-section">
                  <h3 className="result-title">{title}</h3>
                  <span className="result-path">Path: {path}</span>
                </div>
                <span className="match-badge">{matchPercent}% match</span>
              </div>

              {/* Text Content Preview */}
              <div className="text-preview-section">
                <div 
                  className="text-preview"
                  dangerouslySetInnerHTML={{ 
                    __html: highlightKeywordsInText(textPreview, query) 
                  }}
                />
                {fullText.length > textPreview.length && (
                  <button
                    className="view-text-button"
                    onClick={() => toggleText(index)}
                  >
                    <span>{isTextExpanded ? 'Show less' : 'Show more'}</span>
                    <span className={`caret ${isTextExpanded ? 'expanded' : ''}`}>^</span>
                  </button>
                )}
                {isTextExpanded && fullText.length > textPreview.length && (
                  <div className="full-text-content">
                    <div 
                      className="full-text"
                      dangerouslySetInnerHTML={{ 
                        __html: highlightKeywordsInText(fullText, query) 
                      }}
                    />
                  </div>
                )}
              </div>

              {/* HTML View Button */}
              <button
                className="view-html-button"
                onClick={() => toggleHtml(index)}
              >
                <span className="html-icon">&lt;&gt;</span> View HTML
                <span className={`caret ${isHtmlExpanded ? 'expanded' : ''}`}>^</span>
              </button>

              {isHtmlExpanded && (
                <div className="html-content">
                  <pre className="html-code">
                    <code 
                      dangerouslySetInnerHTML={{ 
                        __html: highlightKeywordsInCode(htmlContent, query) 
                      }}
                    />
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ResultsDisplay;
