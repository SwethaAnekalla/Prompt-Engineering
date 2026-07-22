import React, { useState } from 'react';
import axios from 'axios';
import './index.css';
import { useEffect } from "react";
import { supabase } from "./lib/supabase";

import Login from "./pages/Login";
import Signup from "./pages/Signup";

function App() {

  const [session, setSession] = useState(null);
  const [authView, setAuthView] = useState("login");

  
  const [currentView, setCurrentView] = useState('upload'); // upload, search, detail
  const [selectedMeetingId, setSelectedMeetingId] = useState(null);
useEffect(() => {
  supabase.auth.getSession().then(({ data: { session } }) => {
    setSession(session);
  });

  const {
    data: { subscription },
  } = supabase.auth.onAuthStateChange((_event, session) => {
    setSession(session);
  });

  return () => subscription.unsubscribe();
}, []);
  const navigateTo = (view, id = null) => {
    setCurrentView(view);
    if (id) setSelectedMeetingId(id);
  };

 if (!session) {
    return authView === "login" ? (
      <Login onSignup={() => setAuthView("signup")} />
    ) : (
      <Signup onLogin={() => setAuthView("login")} />
    );
  }
  return (
    <>
      <nav className="sidebar">
        <div style={{ marginTop: "auto", padding: "20px" }}>
  <button
    className="btn"
    style={{ width: "100%" }}
    onClick={async () => {
      await supabase.auth.signOut();
    }}
  >
    Logout
  </button>
</div>
        <div className="logo">
          <div className="logo-icon">M</div>
          <h2>MinutesAI</h2>
        </div>
        <ul className="nav-links">
          <li>
            <a 
              className={currentView === 'upload' ? 'active' : ''} 
              onClick={() => navigateTo('upload')}
            >
              Upload
            </a>
          </li>
          <li>
            <a 
              className={currentView === 'search' ? 'active' : ''} 
              onClick={() => navigateTo('search')}
            >
              Search History
            </a>
          </li>
        </ul>
      </nav>

      <main className="content">
        {currentView === 'upload' && <UploadView onMeetingProcessed={(id) => navigateTo('detail', id)} />}
        {currentView === 'search' && <SearchHistoryView onSelectMeeting={(id) => navigateTo('detail', id)} />}
        {currentView === 'detail' && selectedMeetingId && (
          <MeetingDetailView 
            meetingId={selectedMeetingId} 
            onBack={() => navigateTo('search')} 
          />
        )}
      </main>
    </>
  );
}

// --- Upload View Component ---
function UploadView({ onMeetingProcessed }) {
  const [status, setStatus] = useState('idle'); // idle, uploading, processing
  const [error, setError] = useState(null);

  const handleFile = async (file) => {
    if (!file.name.endsWith('.txt') && !file.name.endsWith('.docx')) {
      setError('Invalid file type. Please upload a .txt or .docx file.');
      return;
    }

    setError(null);
    setStatus('uploading');
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const uploadRes = await axios.post('/api/upload/transcript', formData);
      const fileId = uploadRes.data.file_id;
      
      setStatus('processing');
      await axios.post(`/api/process/${fileId}`);
      
      setStatus('idle');
      onMeetingProcessed(fileId);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'An error occurred.');
      setStatus('idle');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <section className="view">
      <header>
        <h1>Upload Transcript</h1>
        <p>Upload a .txt or .docx meeting transcript to extract insights.</p>
      </header>
      
      <div className="upload-container glass-panel">
        {status === 'idle' ? (
          <div 
            className="drop-zone"
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-input').click()}
          >
            <div className="drop-icon">📄</div>
            <h3>Drag & drop your transcript</h3>
            <p>or click to browse (.txt, .docx)</p>
            <input 
              type="file" 
              id="file-input" 
              accept=".txt,.docx" 
              hidden 
              onChange={(e) => {
                if (e.target.files.length) handleFile(e.target.files[0]);
              }}
            />
          </div>
        ) : (
          <div className="status-box">
            <div className="spinner"></div>
            <p>{status === 'uploading' ? 'Uploading transcript...' : 'Processing with AI (Parsing, Summarizing, Extracting)... This may take a moment.'}</p>
          </div>
        )}
        
        {error && (
          <div className="error">
            {error}
          </div>
        )}
      </div>
    </section>
  );
}

// --- Search History Component ---
function SearchHistoryView({ onSelectMeeting }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);

  const performSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await axios.get(`/api/search?q=${encodeURIComponent(query)}`);
      setResults(res.data);
      setSearched(true);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="view">
      <header>
        <h1>Search History</h1>
        <p>Find past meetings, topics, and action items.</p>
      </header>
      
      <div className="search-container glass-panel">
        <input 
          type="text" 
          className="search-input"
          placeholder="Search for 'budget' or 'John'..." 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && performSearch()}
        />
        <button className="btn" onClick={performSearch} disabled={loading}>
          {loading ? '...' : 'Search'}
        </button>
      </div>
      
      {searched && results.length === 0 && (
        <div className="empty-state">No results found.</div>
      )}

      <div className="results-grid">
        {results.map((meeting) => (
          <div key={meeting.id} className="result-card" onClick={() => onSelectMeeting(meeting.id)}>
            <h3>{meeting.filename}</h3>
            <div className="result-date">
              {meeting.upload_timestamp ? new Date(meeting.upload_timestamp).toLocaleDateString() : 'Unknown Date'}
            </div>
            <p>{meeting.summary || 'No summary available.'}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

// --- Meeting Detail Component ---
function MeetingDetailView({ meetingId, onBack }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  React.useEffect(() => {
    axios.get(`/api/meetings/${meetingId}`)
      .then(res => setData(res.data))
      .catch(err => setError('Could not load meeting details.'));
  }, [meetingId]);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <div className="spinner" style={{marginTop: '2rem'}}></div>;

  const handleExport = (format) => {
    window.open(`/api/meetings/${meetingId}/export?format=${format}`, '_blank');
  };

  return (
    <section className="view">
      <div className="detail-header">
        <button className="btn icon-btn" onClick={onBack}>← Back</button>
        <div style={{display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center'}}>
          <div>
            <h1>{data.filename}</h1>
            <p>{data.meeting_date || (data.upload_timestamp ? new Date(data.upload_timestamp).toLocaleDateString() : 'Unknown Date')}</p>
          </div>
          <div style={{display: 'flex', gap: '10px'}}>
            <button className="btn icon-btn" onClick={() => handleExport('md')}>Export MD</button>
            <button className="btn" onClick={() => handleExport('pdf')}>Export PDF</button>
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card glass-panel col-span-2">
          <h3>Executive Summary</h3>
          <p>{data.summary || 'No summary generated.'}</p>
          
          <h4>Key Topics</h4>
          <div className="tags-container">
            {(data.key_topics || []).map((t, idx) => (
              <span key={idx} className="tag">{t}</span>
            ))}
          </div>
        </div>

        <div className="card glass-panel">
          <h3>Action Items</h3>
          <ul className="item-list">
            {(data.action_items || []).map((ai, idx) => (
              <li key={idx} className="list-item">
                <p><strong>Task:</strong> {ai.task}</p>
                <div className="item-meta">
                  {ai.owner && <span className="owner-badge">👤 {ai.owner}</span>}
                  {ai.deadline && <span className="deadline-badge">⏰ {ai.deadline}</span>}
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="card glass-panel">
          <h3>Decisions</h3>
          <ul className="item-list">
            {(data.decisions || []).map((d, idx) => (
              <li key={idx} className="list-item">
                <p><strong>Decision:</strong> {d.decision}</p>
                <p className="item-meta">Context: {d.context}</p>
              </li>
            ))}
          </ul>
        </div>

        <div className="card glass-panel">
          <h3>Risks</h3>
          <ul className="item-list">
            {(data.risks || []).map((r, idx) => {
              const sevClass = r.severity ? `risk-${r.severity.toLowerCase()}` : '';
              return (
                <li key={idx} className={`list-item ${sevClass}`}>
                  <p><strong>Risk:</strong> {r.risk}</p>
                  <span className="owner-badge" style={{marginTop: '5px', display: 'inline-block'}}>
                    Severity: {r.severity}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="card glass-panel">
          <h3>Deadlines</h3>
          <ul className="item-list">
            {(data.deadlines || []).map((d, idx) => (
              <li key={idx} className="list-item">
                <p><strong>Deadline:</strong> {d.deadline_text}</p>
                <div className="item-meta">
                  {d.normalized_date && <span className="deadline-badge">📅 {d.normalized_date}</span>}
                  {d.related_task && <span>Task: {d.related_task}</span>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

export default App;
