import { useState, useRef, useEffect } from 'react';
import { 
  ScanLine, 
  Download,
  History
} from 'lucide-react';

function App() {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [language, setLanguage] = useState('python');
  const [viewMode, setViewMode] = useState<'scanner' | 'history'>('scanner');
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const fetchHistory = async () => {
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${API_URL}/history`);
      if (res.ok) {
        const data = await res.json();
        setHistoryItems(data);
      }
    } catch (err) {
      console.error('Failed to fetch history', err);
    }
  };

  const loadHistoryItem = (item: any) => {
    setCode(item.code || '');
    setLanguage(item.language || 'python');
    setResult({
      ai_probability: item.ai_probability,
      details: item.details
    });
    setViewMode('scanner');
  };

  useEffect(() => {
    // Initial health check or setup if needed
  }, []);

  const analyzeCode = async () => {
    if (!code.trim()) {
      setError('Please enter some code to analyze.');
      return;
    }
    setLoading(true);
    setError('');
    
    try {
      const endpoint = '/analyze';
      const body = { code, language };
      
      const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error('Analysis failed');
      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred during analysis.');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score > 0.7) return 'text-red-400';
    if (score > 0.4) return 'text-yellow-400';
    return 'text-[#00e5ff]';
  };

  const getBadgeStyle = (isAI: boolean) => {
    return isAI 
      ? 'bg-red-950 text-red-400 border border-red-900/50' 
      : 'bg-emerald-950 text-emerald-400 border border-emerald-900/50';
  };

  // Generate line numbers for the textarea
  const lineCount = code.split('\n').length;
  const lineNumbers = Array.from({ length: Math.max(25, lineCount) }, (_, i) => i + 1);

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0a0f1c] text-slate-300 font-sans overflow-hidden">
      
      {/* Top Navbar */}
      <nav className="h-16 flex items-center justify-between px-6 border-b border-slate-800 bg-[#0f1524]">
        <div className="flex items-center space-x-8">
          <div className="flex items-center space-x-2">
            <span className="text-[#00e5ff] font-black tracking-wider text-xl">PROVENANCE AI</span>
          </div>
        </div>
      </nav>

      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Sidebar */}
        <aside className="w-64 border-r border-slate-800 bg-[#0f1524] flex flex-col justify-between py-6">
          <div>
            <div className="px-6 mb-8">
              <p className="text-xs font-bold text-slate-500 tracking-widest uppercase mb-1">Provenance</p>
              <p className="text-xs text-slate-600">Forensic Node v1.0.4</p>
            </div>
            
            <nav className="space-y-1">
              <button 
                onClick={() => setViewMode('scanner')}
                className={`w-full flex items-center space-x-3 px-6 py-3 transition-colors ${viewMode === 'scanner' ? 'bg-[#0a0f1c] border-l-2 border-[#00e5ff] text-[#00e5ff]' : 'text-slate-500 hover:text-slate-300 hover:bg-[#0a0f1c]/50'}`}
              >
                <ScanLine className="w-5 h-5" />
                <span className="text-sm font-semibold tracking-wide">CODE SCANNER</span>
              </button>
              <button 
                onClick={() => { setViewMode('history'); fetchHistory(); }}
                className={`w-full flex items-center space-x-3 px-6 py-3 transition-colors ${viewMode === 'history' ? 'bg-[#0a0f1c] border-l-2 border-[#00e5ff] text-[#00e5ff]' : 'text-slate-500 hover:text-slate-300 hover:bg-[#0a0f1c]/50'}`}
              >
                <History className="w-5 h-5" />
                <span className="text-sm font-semibold tracking-wide">HISTORY</span>
              </button>
            </nav>

            <div className="px-6 mt-8">
              <button 
                onClick={() => { setCode(''); setResult(null); setError(''); setViewMode('scanner'); }}
                className="w-full py-2 px-4 border border-slate-700 rounded text-xs font-bold tracking-widest text-[#00e5ff] hover:bg-slate-800 transition-colors flex justify-center items-center space-x-2"
              >
                <span>+ NEW ANALYSIS</span>
              </button>
            </div>
          </div>

          <div className="px-6 space-y-4">
            <p className="text-[10px] text-slate-600 mt-4 uppercase tracking-widest">© 2024 PROVENANCE AI.</p>
          </div>
        </aside>

        {/* Main Area */}
        <main className="flex-1 flex flex-col bg-[#0a0f1c] relative">
          
          {viewMode === 'history' ? (
            <div className="flex-1 overflow-y-auto p-8">
              <h1 className="text-2xl font-bold text-slate-200 mb-6 font-mono tracking-tight flex items-center">
                <History className="mr-3 text-[#00e5ff]" />
                Scan History
              </h1>
              
              <div className="space-y-4">
                {historyItems.length === 0 ? (
                  <div className="text-slate-500 font-mono">No scans found. Run a code scan to see it here.</div>
                ) : (
                  historyItems.map((item, idx) => (
                    <div 
                      key={idx} 
                      onClick={() => loadHistoryItem(item)}
                      className="bg-[#0f1524] border border-slate-800 p-4 rounded-lg cursor-pointer hover:border-[#00e5ff]/50 transition-colors group flex items-start justify-between"
                    >
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${getBadgeStyle(item.ai_probability > 0.5)}`}>
                            {item.ai_probability > 0.5 ? 'AI' : 'HUMAN'}
                          </span>
                          <span className="text-[10px] text-[#00e5ff] font-mono border border-[#00e5ff]/30 px-1.5 rounded uppercase">
                            {item.language}
                          </span>
                          <span className="text-xs text-slate-500 font-mono">
                            {new Date(item.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="text-sm font-mono text-slate-300 line-clamp-2 bg-[#0a0f1c] p-2 rounded border border-slate-800/50">
                          {item.code.substring(0, 150)}...
                        </div>
                      </div>
                      <div className="ml-6 flex flex-col items-end">
                        <span className={`text-3xl font-bold tracking-tighter ${getScoreColor(item.ai_probability)}`}>
                          {Math.round(item.ai_probability * 100)}%
                        </span>
                        <span className="text-[10px] text-slate-500 uppercase tracking-widest mt-1 group-hover:text-[#00e5ff] transition-colors">
                          View Details &rarr;
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <>
              {/* Editor Header */}
              <div className="h-12 border-b border-slate-800 flex items-center justify-between px-4 bg-[#0a0f1c]">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-mono text-slate-300">input_source.{language === 'python' ? 'py' : language === 'javascript' ? 'js' : 'txt'}</span>
                    <div className="w-2 h-2 rounded-full bg-[#00e5ff]"></div>
                  </div>
                  
                  <select 
                    value={language} 
                    onChange={(e) => setLanguage(e.target.value)}
                    className="bg-slate-800 border-none text-[10px] font-bold text-[#00e5ff] uppercase tracking-widest px-2 py-1 rounded cursor-pointer outline-none hover:bg-slate-700 transition-colors"
                  >
                    <option value="python">Python</option>
                    <option value="javascript">JavaScript</option>
                    <option value="typescript">TypeScript</option>
                    <option value="c++">C++</option>
                    <option value="java">Java</option>
                  </select>
                </div>
                <div className="flex space-x-6">
                  <button onClick={analyzeCode} disabled={loading} className="text-xs font-bold text-[#00e5ff] hover:text-white uppercase tracking-wider">
                    {loading ? 'Analyzing...' : 'Run Scan'}
                  </button>
                </div>
              </div>
              
              {error && (
                <div className="absolute top-16 left-1/2 transform -translate-x-1/2 bg-red-950 border border-red-900 text-red-400 px-4 py-2 rounded text-sm z-10 shadow-lg">
                  {error}
                </div>
              )}

              <div className="flex-1 flex flex-col overflow-hidden relative">
                <div className="flex-1 flex overflow-hidden relative">
                  <div className="w-12 bg-[#0a0f1c] border-r border-slate-800/50 flex flex-col items-center py-4 font-mono text-xs text-slate-700 select-none overflow-hidden">
                    {lineNumbers.map(n => <div key={n} className="leading-6">{n}</div>)}
                  </div>
                  <textarea
                    ref={textareaRef}
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="# Paste code for forensic analysis..."
                    className="flex-1 bg-transparent text-slate-300 font-mono text-sm p-4 resize-none focus:outline-none leading-6 whitespace-pre"
                    spellCheck="false"
                  />
                </div>
              </div>
            </>
          )}
        </main>

        {/* Right Panel - Forensic Insights */}
        <aside className="w-[380px] border-l border-slate-800 bg-[#0f1524] flex flex-col overflow-y-auto">
          <div className="p-6">
            <h2 className="text-xs font-bold text-slate-500 tracking-widest uppercase mb-6">Forensic Insights</h2>
            
            <div className="bg-[#0a0f1c] border border-slate-800 rounded-lg p-6 mb-8 relative overflow-hidden">
              <h3 className="text-[10px] font-bold tracking-widest text-[#00e5ff] uppercase mb-4">AI Probability Score</h3>
              <div className="flex items-baseline space-x-1">
                <span className={`text-6xl font-bold tracking-tighter ${result ? getScoreColor(result.ai_probability) : 'text-slate-600'}`}>
                  {result ? Math.round(result.ai_probability * 100) : '--'}
                </span>
                <span className="text-2xl text-[#00e5ff] font-light">%</span>
              </div>
              <div className="mt-6 w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-[#00e5ff] transition-all duration-1000 ease-out" 
                  style={{ width: result ? `${result.ai_probability * 100}%` : '0%' }}
                ></div>
              </div>
            </div>

            <h2 className="text-xs font-bold text-slate-500 tracking-widest uppercase mb-4">Detected Patterns</h2>
            
            <div className="space-y-4">
              {/* Pattern 1: Confidence Score */}
              {result && (
                <div className="bg-[#0a0f1c] border border-slate-800 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <h4 className="text-sm font-semibold text-slate-200">Confidence Rating</h4>
                    <div className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-slate-800 text-[#00e5ff] border border-slate-700">
                      {Math.round(result.details.confidence_score * 100)}%
                    </div>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    {result.details.confidence_score > 0.8 
                      ? "High consensus between heuristic patterns and transformer analysis."
                      : result.details.confidence_score > 0.5
                      ? "Moderate consensus. Heuristics and NLP models show some disagreement."
                      : "Low consensus. The models are providing conflicting signals."}
                  </p>
                </div>
              )}


              {/* Pattern 2: Artifacts */}
              {result && result.details.artifact_score > 0 && (
                <div className="bg-red-950/20 border border-red-900/50 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <h4 className="text-sm font-semibold text-red-400">AI Artifacts Detected</h4>
                    <div className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-red-900 text-red-200">
                      {Math.round(result.details.artifact_score * 100)}%
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Identified specific phrases (e.g. "Here is the code") or boilerplate structures (e.g. `if __name__ == "__main__": main()`) commonly generated by LLMs.
                  </p>
                </div>
              )}

              {/* Pattern 3: Entropy */}
              <div className="bg-[#0a0f1c] border border-slate-800 rounded-lg p-4">
                <div className="flex justify-between items-start mb-3">
                  <h4 className="text-sm font-semibold text-slate-200">Shannon Entropy</h4>
                  <div className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${result && (result.details.entropy > 4.2 && result.details.entropy < 5.0) ? getBadgeStyle(true) : getBadgeStyle(false)}`}>
                    {result ? ((result.details.entropy > 4.2 && result.details.entropy < 5.0) ? 'AI-LIKE' : 'NATURAL') : '---'}
                  </div>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {result ? 
                    (result.details.entropy > 4.2 && result.details.entropy < 5.0
                      ? `Entropy level (${result.details.entropy}) is within the tight predictability range typical of LLMs.` 
                      : `Entropy level (${result.details.entropy}) shows organic variance found in human coding.`)
                    : 'Awaiting analysis...'
                  }
                </p>
              </div>

              {/* Pattern 4 */}
              <div className="bg-[#0a0f1c] border border-slate-800 rounded-lg p-4">
                <div className="flex justify-between items-start mb-3">
                  <h4 className="text-sm font-semibold text-slate-200">Comment Density</h4>
                  <div className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${result && result.details.heuristic_score_comment > 0.5 ? getBadgeStyle(true) : getBadgeStyle(false)}`}>
                    {result ? (result.details.heuristic_score_comment > 0.5 ? 'AI' : 'HUMAN') : '---'}
                  </div>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {result ? 
                    (result.details.heuristic_score_comment > 0.5 
                      ? `Overly formal documentation detected (Ratio: ${result.details.comment_ratio}). Highly characteristic of LLM output.` 
                      : `Comment ratio (${result.details.comment_ratio}) aligns with typical human coding practices.`)
                    : 'Awaiting analysis...'
                  }
                </p>
              </div>

              {/* Pattern 2 */}
              <div className="bg-[#0a0f1c] border border-slate-800 rounded-lg p-4">
                <div className="flex justify-between items-start mb-3">
                  <h4 className="text-sm font-semibold text-slate-200">Variable Naming Anchor</h4>
                  <div className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${result && result.details.heuristic_score_words > 0.5 ? getBadgeStyle(true) : getBadgeStyle(false)}`}>
                    {result ? (result.details.heuristic_score_words > 0.5 ? 'AI' : 'HUMAN') : '---'}
                  </div>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {result ? 
                    (result.details.heuristic_score_words > 0.5 
                      ? `Highly generic, overly descriptive variable names (Avg len: ${result.details.avg_word_length}). Matches LLM conventions.` 
                      : `Variable naming conventions (Avg len: ${result.details.avg_word_length}) show domain-specific entropy.`)
                    : 'Awaiting analysis...'
                  }
                </p>
              </div>

              {/* Pattern 3: Structural Analysis */}
              {result && result.details.ast_supported ? (
                <>
                  <div className="bg-[#0a0f1c] border border-slate-800 rounded-lg p-4">
                    <div className="flex justify-between items-start mb-3">
                      <h4 className="text-sm font-semibold text-slate-200">Cyclomatic Complexity</h4>
                      <div className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${result.details.avg_complexity < 2.0 ? getBadgeStyle(true) : getBadgeStyle(false)}`}>
                        {result.details.avg_complexity < 2.0 ? 'AI' : 'HUMAN'}
                      </div>
                    </div>
                    <p className="text-xs text-slate-500 leading-relaxed">
                      {result.details.avg_complexity < 2.0 
                        ? `Extremely low avg complexity (${result.details.avg_complexity.toFixed(1)}). AI often generates overly simplified structural flows.`
                        : `Average complexity (${result.details.avg_complexity.toFixed(1)}) indicates natural human logical variance.`}
                    </p>
                  </div>

                  <div className="bg-[#0a0f1c] border border-slate-800 rounded-lg p-4">
                    <div className="flex justify-between items-start mb-3">
                      <h4 className="text-sm font-semibold text-slate-200">Docstring Ratio</h4>
                      <div className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${result.details.docstring_ratio > 0.6 ? getBadgeStyle(true) : getBadgeStyle(false)}`}>
                        {result.details.docstring_ratio > 0.6 ? 'AI' : 'HUMAN'}
                      </div>
                    </div>
                    <p className="text-xs text-slate-500 leading-relaxed">
                      {result.details.docstring_ratio > 0.6 
                        ? `Suspiciously perfect documentation. ${Math.round(result.details.docstring_ratio * 100)}% of structures have docstrings.`
                        : `Documentation ratio (${Math.round(result.details.docstring_ratio * 100)}%) aligns with human organic development.`}
                    </p>
                  </div>
                </>
              ) : (
                <div className="bg-[#0a0f1c] border border-slate-800 rounded-lg p-4 opacity-70">
                  <div className="flex justify-between items-start mb-3">
                    <h4 className="text-sm font-semibold text-slate-200">Logic Flow Entropy</h4>
                    <div className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-slate-800 text-slate-500 border border-slate-700">
                      PENDING
                    </div>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Structural analysis of AST (Abstract Syntax Tree) is not supported for this language or pending analysis.
                  </p>
                </div>
              )}

            </div>
          </div>
          
          <div className="mt-auto border-t border-slate-800 p-6 bg-[#0a0f1c]">
            <div className="flex justify-between items-end mb-4">
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">Engine Status</p>
                <div className="flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                  <p className="text-xs font-bold text-slate-300 uppercase">
                    FORENSIC ENGINE ACTIVE
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">Timestamp</p>
                <p className="text-xs font-bold text-slate-300 uppercase">
                  {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </p>
              </div>
            </div>
            <button 
              disabled={!result}
              className={`w-full py-3 bg-white text-black text-sm font-bold rounded flex items-center justify-center space-x-2 transition-colors ${!result ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-200'}`}
            >
              <Download className="w-4 h-4" />
              <span>Export Report</span>
            </button>
          </div>
        </aside>

      </div>
    </div>
  );
}

export default App;
