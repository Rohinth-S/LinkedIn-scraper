import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const LLM_PROVIDERS = [
  { value: 'openai', label: 'OpenAI GPT', description: 'Using GPT-3.5-turbo for query parsing' },
  { value: 'claude', label: 'Anthropic Claude', description: 'Using Claude-3-haiku for query parsing' },
  { value: 'gemini', label: 'Google Gemini', description: 'Using Gemini Pro for query parsing' }
];

function App() {
  const [activeTab, setActiveTab] = useState('search');
  const [credentials, setCredentials] = useState({
    linkedin_email: '',
    linkedin_password: '',
    openai_api_key: '',
    claude_api_key: '',
    gemini_api_key: '',
    hunter_api_key: ''
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLLM, setSelectedLLM] = useState('openai');
  const [maxResults, setMaxResults] = useState(50);
  const [isLoading, setIsLoading] = useState(false);
  const [scrapingJobs, setScrapingJobs] = useState([]);
  const [currentJob, setCurrentJob] = useState(null);
  const [parsedQuery, setParsedQuery] = useState(null);

  useEffect(() => {
    loadCredentials();
    loadJobs();
  }, []);

  const loadCredentials = async () => {
    try {
      const response = await axios.get(`${API}/credentials`);
      setCredentials(response.data);
    } catch (error) {
      console.error('Failed to load credentials:', error);
    }
  };

  const loadJobs = async () => {
    try {
      const response = await axios.get(`${API}/scraping-jobs`);
      setScrapingJobs(response.data);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    }
  };

  const saveCredentials = async () => {
    try {
      setIsLoading(true);
      await axios.post(`${API}/credentials`, credentials);
      alert('Credentials saved successfully!');
    } catch (error) {
      alert('Failed to save credentials: ' + error.response?.data?.detail);
    } finally {
      setIsLoading(false);
    }
  };

  const parseQuery = async () => {
    if (!searchQuery.trim()) {
      alert('Please enter a search query');
      return;
    }

    try {
      setIsLoading(true);
      const response = await axios.post(`${API}/parse-query`, {
        query: searchQuery,
        llm_provider: selectedLLM,
        max_results: maxResults
      });
      setParsedQuery(response.data);
    } catch (error) {
      alert('Failed to parse query: ' + error.response?.data?.detail);
    } finally {
      setIsLoading(false);
    }
  };

  const startScraping = async () => {
    if (!searchQuery.trim()) {
      alert('Please enter a search query');
      return;
    }

    try {
      setIsLoading(true);
      const response = await axios.post(`${API}/start-scraping`, {
        query: searchQuery,
        llm_provider: selectedLLM,
        max_results: maxResults
      });
      setCurrentJob(response.data);
      setActiveTab('jobs');
      loadJobs();
      
      // Poll for job updates
      pollJobStatus(response.data.id);
    } catch (error) {
      alert('Failed to start scraping: ' + error.response?.data?.detail);
    } finally {
      setIsLoading(false);
    }
  };

  const pollJobStatus = (jobId) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API}/scraping-jobs/${jobId}`);
        const job = response.data;
        
        setCurrentJob(job);
        
        if (job.status === 'completed' || job.status === 'failed') {
          clearInterval(interval);
          loadJobs();
        }
      } catch (error) {
        console.error('Failed to poll job status:', error);
        clearInterval(interval);
      }
    }, 3000);
  };

  const downloadCSV = async (jobId) => {
    try {
      const response = await axios.get(`${API}/export-csv/${jobId}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `linkedin_leads_${jobId}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      alert('Failed to download CSV: ' + error.response?.data?.detail);
    }
  };

  const getStatusBadge = (status) => {
    const statusColors = {
      pending: 'bg-yellow-100 text-yellow-800',
      running: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800'
    };

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[status] || 'bg-gray-100 text-gray-800'}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <img 
                  src="https://images.pexels.com/photos/1083792/pexels-photo-1083792.jpeg?auto=compress&cs=tinysrgb&w=100" 
                  alt="LinkedIn Lead Generation" 
                  className="h-10 w-10 rounded-lg object-cover"
                />
              </div>
              <div className="ml-4">
                <h1 className="text-2xl font-bold text-gray-900">LinkedIn Lead Generator</h1>
                <p className="text-sm text-gray-500">AI-Powered Lead Discovery for Sales Teams</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-500">
                Production Ready • LLM Agnostic
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('search')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'search'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Search & Scrape
            </button>
            <button
              onClick={() => setActiveTab('credentials')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'credentials'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              API Credentials
            </button>
            <button
              onClick={() => setActiveTab('jobs')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'jobs'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Scraping Jobs
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          
          {/* Search Tab */}
          {activeTab === 'search' && (
            <div className="space-y-6">
              {/* Hero Section */}
              <div className="relative bg-gradient-to-r from-blue-600 to-indigo-700 rounded-xl p-8 text-white">
                <div className="absolute inset-0 bg-black opacity-20 rounded-xl"></div>
                <div className="relative">
                  <h2 className="text-3xl font-bold mb-4">Find Your Perfect Leads</h2>
                  <p className="text-xl opacity-90 mb-6">
                    Use natural language to discover LinkedIn profiles for your outreach campaigns
                  </p>
                  <div className="flex items-center space-x-4 text-sm">
                    <span className="bg-white/20 px-3 py-1 rounded-full">Real LinkedIn Data</span>
                    <span className="bg-white/20 px-3 py-1 rounded-full">AI-Powered Parsing</span>
                    <span className="bg-white/20 px-3 py-1 rounded-full">CSV Export Ready</span>
                  </div>
                </div>
              </div>

              {/* Search Form */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Search Configuration</h3>
                
                <div className="space-y-4">
                  {/* Natural Language Query */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Natural Language Query
                    </label>
                    <textarea
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Example: Find all vendor managers or heads of digital transformation in the US where companies have an employee count 500+"
                    />
                  </div>

                  {/* LLM Provider Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      AI Provider for Query Parsing
                    </label>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {LLM_PROVIDERS.map((provider) => (
                        <div key={provider.value} className="relative">
                          <input
                            type="radio"
                            id={provider.value}
                            name="llm_provider"
                            value={provider.value}
                            checked={selectedLLM === provider.value}
                            onChange={(e) => setSelectedLLM(e.target.value)}
                            className="sr-only"
                          />
                          <label
                            htmlFor={provider.value}
                            className={`block p-4 border rounded-lg cursor-pointer ${
                              selectedLLM === provider.value
                                ? 'border-blue-500 bg-blue-50'
                                : 'border-gray-300 hover:border-gray-400'
                            }`}
                          >
                            <div className="font-medium text-gray-900">{provider.label}</div>
                            <div className="text-sm text-gray-500">{provider.description}</div>
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Max Results */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Maximum Results
                    </label>
                    <select
                      value={maxResults}
                      onChange={(e) => setMaxResults(parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value={25}>25 profiles</option>
                      <option value={50}>50 profiles</option>
                      <option value={100}>100 profiles</option>
                      <option value={200}>200 profiles</option>
                    </select>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex space-x-4">
                    <button
                      onClick={parseQuery}
                      disabled={isLoading}
                      className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                      {isLoading ? 'Parsing...' : 'Parse Query'}
                    </button>
                    <button
                      onClick={startScraping}
                      disabled={isLoading}
                      className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                    >
                      {isLoading ? 'Starting...' : 'Start Scraping'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Parsed Query Display */}
              {parsedQuery && (
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Parsed Query</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h4 className="font-medium text-gray-700">Target Roles</h4>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {parsedQuery.roles.map((role, index) => (
                          <span key={index} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                            {role}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-700">Locations</h4>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {parsedQuery.locations.map((location, index) => (
                          <span key={index} className="bg-green-100 text-green-800 px-2 py-1 rounded text-sm">
                            {location}
                          </span>
                        ))}
                      </div>
                    </div>
                    {parsedQuery.company_size_min && (
                      <div>
                        <h4 className="font-medium text-gray-700">Company Size</h4>
                        <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-sm">
                          {parsedQuery.company_size_min}+ employees
                        </span>
                      </div>
                    )}
                    {parsedQuery.seniority_levels.length > 0 && (
                      <div>
                        <h4 className="font-medium text-gray-700">Seniority Levels</h4>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {parsedQuery.seniority_levels.map((level, index) => (
                            <span key={index} className="bg-orange-100 text-orange-800 px-2 py-1 rounded text-sm">
                              {level}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Credentials Tab */}
          {activeTab === 'credentials' && (
            <div className="space-y-6">
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">API Credentials Configuration</h3>
                <p className="text-sm text-gray-600 mb-6">
                  Configure your API credentials for LinkedIn scraping and LLM providers. All credentials are stored securely.
                </p>

                <div className="space-y-6">
                  {/* LinkedIn Credentials */}
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h4 className="font-medium text-gray-900 mb-3">LinkedIn Account (Required)</h4>
                    <p className="text-sm text-gray-600 mb-4">
                      Use a dedicated LinkedIn account for scraping to avoid personal account restrictions.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                        <input
                          type="email"
                          value={credentials.linkedin_email || ''}
                          onChange={(e) => setCredentials({...credentials, linkedin_email: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="linkedin@example.com"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                        <input
                          type="password"
                          value={credentials.linkedin_password === '••••••••' ? '' : credentials.linkedin_password || ''}
                          onChange={(e) => setCredentials({...credentials, linkedin_password: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="••••••••"
                        />
                      </div>
                    </div>
                  </div>

                  {/* LLM Provider Credentials */}
                  <div className="bg-green-50 p-4 rounded-lg">
                    <h4 className="font-medium text-gray-900 mb-3">LLM Provider API Keys</h4>
                    <p className="text-sm text-gray-600 mb-4">
                      Configure at least one LLM provider for natural language query parsing.
                    </p>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          OpenAI API Key
                          <span className="text-xs text-gray-500 ml-2">
                            (Get from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">OpenAI Platform</a>)
                          </span>
                        </label>
                        <input
                          type="password"
                          value={credentials.openai_api_key || ''}
                          onChange={(e) => setCredentials({...credentials, openai_api_key: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="sk-..."
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Anthropic Claude API Key
                          <span className="text-xs text-gray-500 ml-2">
                            (Get from <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Anthropic Console</a>)
                          </span>
                        </label>
                        <input
                          type="password"
                          value={credentials.claude_api_key || ''}
                          onChange={(e) => setCredentials({...credentials, claude_api_key: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="sk-ant-..."
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Google Gemini API Key
                          <span className="text-xs text-gray-500 ml-2">
                            (Get from <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Google AI Studio</a>)
                          </span>
                        </label>
                        <input
                          type="password"
                          value={credentials.gemini_api_key || ''}
                          onChange={(e) => setCredentials({...credentials, gemini_api_key: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="AI..."
                        />
                      </div>
                    </div>
                  </div>

                  {/* Optional Enrichment */}
                  <div className="bg-yellow-50 p-4 rounded-lg">
                    <h4 className="font-medium text-gray-900 mb-3">Email Enrichment (Optional)</h4>
                    <p className="text-sm text-gray-600 mb-4">
                      Enable email discovery for extracted profiles using Hunter.io.
                    </p>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Hunter.io API Key
                        <span className="text-xs text-gray-500 ml-2">
                          (Get from <a href="https://hunter.io/api_keys" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Hunter.io Dashboard</a>)
                        </span>
                      </label>
                      <input
                        type="password"
                        value={credentials.hunter_api_key || ''}
                        onChange={(e) => setCredentials({...credentials, hunter_api_key: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Optional for email enrichment"
                      />
                    </div>
                  </div>

                  {/* Save Button */}
                  <div className="flex justify-end">
                    <button
                      onClick={saveCredentials}
                      disabled={isLoading}
                      className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                      {isLoading ? 'Saving...' : 'Save Credentials'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Jobs Tab */}
          {activeTab === 'jobs' && (
            <div className="space-y-6">
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900">Scraping Jobs</h3>
                  <p className="text-sm text-gray-600">Monitor and download your LinkedIn scraping results</p>
                </div>
                
                <div className="divide-y divide-gray-200">
                  {scrapingJobs.length === 0 ? (
                    <div className="px-6 py-8 text-center text-gray-500">
                      No scraping jobs yet. Start your first search!
                    </div>
                  ) : (
                    scrapingJobs.map((job) => (
                      <div key={job.id} className="px-6 py-4">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-3">
                              <h4 className="font-medium text-gray-900 truncate max-w-md">
                                "{job.original_query}"
                              </h4>
                              {getStatusBadge(job.status)}
                            </div>
                            <div className="mt-1 text-sm text-gray-500">
                              Started: {new Date(job.created_at).toLocaleString()}
                              {job.completed_at && (
                                <span className="ml-4">
                                  Completed: {new Date(job.completed_at).toLocaleString()}
                                </span>
                              )}
                            </div>
                            {job.status === 'completed' && (
                              <div className="mt-1 text-sm text-green-600">
                                ✓ Found {job.profiles_found} profiles
                              </div>
                            )}
                            {job.status === 'failed' && job.error_message && (
                              <div className="mt-1 text-sm text-red-600">
                                ✗ {job.error_message}
                              </div>
                            )}
                          </div>
                          <div className="flex items-center space-x-2">
                            {job.status === 'completed' && job.profiles_found > 0 && (
                              <button
                                onClick={() => downloadCSV(job.id)}
                                className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700"
                              >
                                Download CSV
                              </button>
                            )}
                            {job.status === 'running' && (
                              <div className="flex items-center space-x-2 text-blue-600">
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                                <span className="text-sm">Scraping...</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Current Job Status */}
              {currentJob && (
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Current Job Status</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Job ID:</span>
                      <span className="text-gray-600">{currentJob.id}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Status:</span>
                      {getStatusBadge(currentJob.status)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Profiles Found:</span>
                      <span className="text-gray-600">{currentJob.profiles_found}</span>
                    </div>
                    {currentJob.status === 'completed' && currentJob.profiles_found > 0 && (
                      <div className="pt-4">
                        <button
                          onClick={() => downloadCSV(currentJob.id)}
                          className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                        >
                          Download CSV Export
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;