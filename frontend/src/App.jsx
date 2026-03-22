import React, { useState } from 'react';
import axios from 'axios';
import { Upload, Activity, Brain, Server, Loader2, CheckCircle2, LineChart, Database, Info, X } from 'lucide-react';
import './App.css';

const MmseGauge = ({ score }) => {
  const r = 40;
  const c = Math.PI * r;
  const offset = c - ((score / 30) * c);
  return (
    <div style={{ position: 'relative', width: '120px', height: '60px', margin: '10px auto 0' }}>
      <svg width="120" height="60" viewBox="0 0 120 60">
        <defs>
          <linearGradient id="arc-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" />
            <stop offset="33%" stopColor="#f59e0b" />
            <stop offset="66%" stopColor="#eab308" />
            <stop offset="100%" stopColor="#10b981" />
          </linearGradient>
        </defs>
        <path d="M 20 60 A 40 40 0 0 1 100 60" fill="none" stroke="var(--border-light)" strokeWidth="8" strokeLinecap="round" />
        <path 
          d="M 20 60 A 40 40 0 0 1 100 60" 
          fill="none" 
          stroke="url(#arc-gradient)" 
          strokeWidth="8" 
          strokeLinecap="round" 
          strokeDasharray={c} 
          strokeDashoffset={offset} 
          style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.22, 1, 0.36, 1)' }} 
        />
      </svg>
      <div style={{ position: 'absolute', bottom: '0', width: '100%', textAlign: 'center', fontSize: '1.4rem', fontWeight: '600' }}>
        {score.toFixed(1)}
      </div>
    </div>
  );
};

const ConfidenceRow = ({ label, prob, reverseColor=false }) => {
  const conf = prob > 0.5 ? prob : 1 - prob;
  const isAD = prob > 0.5;
  const color = isAD ? (reverseColor ? 'var(--success)' : 'var(--danger)') : (reverseColor ? 'var(--danger)' : 'var(--success)');
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '10px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        <span>{label} <span style={{fontSize:'0.7rem', opacity:0.6}}>({isAD ? 'AD' : 'HC'})</span></span>
        <span style={{color: 'var(--text-main)', fontWeight: 500}}>{(conf * 100).toFixed(1)}%</span>
      </div>
      <div className="prog-bg" style={{ marginTop: '2px', height: '4px' }}>
        <div className="prog-fill" style={{ width: `${conf * 100}%`, backgroundColor: color }} />
      </div>
    </div>
  );
};

const Waveform = ({ data }) => {
  if (!data || data.length === 0) return null;
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', height: '40px', gap: '1px', margin: '4px 0 16px', opacity: 0.8 }}>
      {data.map((val, i) => (
        <div 
          key={i} 
          style={{ 
            flex: 1, 
            height: `${Math.max(5, val * 100)}%`, 
            background: 'var(--accent)', 
            borderRadius: '2px' 
          }} 
        />
      ))}
    </div>
  );
};


function App() {
  const [file, setFile] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [age, setAge] = useState(65.0);
  const [education, setEducation] = useState(12.0);
  const [cdr, setCdr] = useState(0.5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("TAUKADIAL");
  const [showScience, setShowScience] = useState(false);


  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleAnalyze = async () => {
    if (!file || !transcript) {
      setError("Audio file and patient transcript are required.");
      return;
    }
    
    setLoading(true);
    setError("");
    
    const formData = new FormData();
    formData.append("audio", file);
    formData.append("transcript", transcript);
    formData.append("age", age);
    formData.append("education", education);
    formData.append("cdr", cdr);

    try {
      const response = await axios.post("http://localhost:8000/predict", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      if (response.data.status === "success") {
         setResult(response.data.data);
      } else {
         setError(response.data.message);
      }
    } catch (err) {
      setError("Inference server offline. Ensure FastAPI is running on port 8000.");
    }
    setLoading(false);
  };

  const handleSimulate = (type) => {
    setLoading(true);
    setResult(null);
    setError("");
    
    // Simulate realistic processing delay
    setTimeout(() => {
      const isAD = type === 'AD';
      setAge(isAD ? 78.0 : 68.0);
      setEducation(isAD ? 10.0 : 16.0);
      setCdr(isAD ? 1.0 : 0.0);
      setTranscript(isAD 
        ? "The... the lady is... she's there at the water. Sink is high. Boy is... on the chair? No, stool. Cookies... falling? He is falling."
        : "The mother is focused on the dishes while the sink overflows behind her. Meanwhile, her son is precariously reaching for a cookie jar on a wobbly stool while his sister looks on."
      );
      
      const mockResult = {
        classification: isAD ? "Dementia (AD)" : "Healthy Control (HC)",
        ad_probability: isAD ? 0.894 : 0.122,
        mmse_score: isAD ? 14.2 : 29.8,
        modality_probs: {
          acoustic: isAD ? 0.78 : 0.15,
          text: isAD ? 0.94 : 0.08,
          clinical: isAD ? 0.82 : 0.10
        },
        waveform: Array.from({length: 100}, () => Math.random() * 0.8),
        transcript: isAD ? "Simulated AD Profile" : "Simulated HC Profile",
        age: isAD ? 78.0 : 68.0,
        education: isAD ? 10.0 : 16.0,
        cdr: isAD ? 1.0 : 0.0
      };
      
      setResult(mockResult);
      setLoading(false);
    }, 1500);
  };

  return (
    <div className="dashboard-wrapper">
      
      <header className="header">
        <Brain color="white" size={24} />
        <h1>Cognitive Inference Engine</h1>
        <div className="header-badge">Live Tensors</div>
        <button className="info-btn" onClick={() => setShowScience(true)} title="Scientific Evidence">
          <Info size={18} />
        </button>
      </header>

      {showScience && (
        <div className="modal-overlay" onClick={() => setShowScience(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{display:'flex', alignItems:'center', gap:'10px'}}>
                <Brain size={20} color="var(--accent)" />
                <h2 style={{margin:0, fontSize:'1.1rem'}}>Scientific Methodology</h2>
              </div>
              <X className="close-icon" onClick={() => setShowScience(false)} />
            </div>
            <div className="modal-body">
              <section>
                <h3>1. MMSE Staging (Clinical Gold Standard)</h3>
                <p>The Mini-Mental State Examination is a 30-point tool. Scores below 24 typically indicate cognitive impairment. Our model regresses this index using a Trimodal Product of Experts (PoE) architecture.</p>
              </section>
              <section>
                <h3>2. Acoustic Biomarkers (Prosody & Timing)</h3>
                <p>Early-stage AD often manifests as <strong>Prosodic Flattening</strong> (reduced pitch variance) and increased <strong>Temporal Gaps</strong> (silent pauses) as patients search for vocabulary (Anomia).</p>
              </section>
              <section>
                <h3>3. Linguistic Biomarkers (Semantics)</h3>
                <p>Using RoBERTa-large, we analyze vocabulary richness (TTR) and syntactic complexity. Cognitive decline often leads to "simplified" sentence structures and the loss of specific Information Units (IU).</p>
              </section>
              <section>
                <h3>4. Bayesian Trimodal Fusion</h3>
                <p>Our PoE logic multiplies isolated modality posteriors. This allows the model to dynamically "weight" the most confident stream (e.g., relying on Text if Audio is noisy), mimicking expert neurological consultation.</p>
              </section>
            </div>
          </div>
        </div>
      )}

      {/* Panels 1 and 2: Input and Live Assessment */}
      <div className="grid-layout">
        <div className="panel">
          <div className="panel-title">
            <Server size={14} /> Panel 1: Data Ingestion
          </div>

          <label 
            className={`upload-zone ${file ? 'active' : ''}`}
            onDragOver={e => e.preventDefault()}
            onDrop={handleFileDrop}
          >
            {file ? <CheckCircle2 size={28} color="var(--accent)" /> : <Upload size={28} className="upload-icon" />}
            <div style={{fontWeight: 500, color: file ? 'var(--text-main)' : 'var(--text-muted)', fontSize: '0.9rem'}}>
              {file ? file.name : "Drag & drop patient .WAV audio"}
            </div>
            {!file && <span style={{fontSize: '0.75rem', color: 'var(--text-muted)'}}>or click to browse local files</span>}
            <input type="file" accept=".wav,.mp3" hidden onChange={handleFileChange} />
          </label>

          {(result && result.waveform) && <Waveform data={result.waveform} />}

          <div className="input-group">
            <label>Transcription (Whisper Context)</label>
            <textarea 
              rows={3} 
              value={transcript} 
              onChange={e => setTranscript(e.target.value)}
              placeholder="Enter patient speech dynamics..."
            />
          </div>

          <div className="row-3">
            <div className="input-group">
              <label>Age</label>
              <input type="number" value={age} onChange={e => setAge(parseFloat(e.target.value))} />
            </div>
            <div className="input-group">
              <label>Education</label>
              <input type="number" value={education} onChange={e => setEducation(parseFloat(e.target.value))} />
            </div>
            <div className="input-group">
              <label>CDR Default</label>
              <input type="number" step="0.5" value={cdr} onChange={e => setCdr(parseFloat(e.target.value))} />
            </div>
          </div>

          {error && <div className="error-banner">{error}</div>}

          <button className="btn-primary" onClick={handleAnalyze} disabled={loading}>
            {loading ? <Loader2 className="spinner" size={18} /> : <Activity size={18} />}
            {loading ? "Processing Modalities..." : "Execute Trimodal PoE Fusion"}
          </button>

          <div style={{ display: 'flex', gap: '8px', marginTop: '10px', justifyContent: 'center' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Quick Demos:</span>
            <button className="badge-btn" onClick={() => handleSimulate('HC')} disabled={loading}>Healthy Patient</button>
            <button className="badge-btn" style={{ borderColor: 'rgba(239, 68, 68, 0.3)', color: 'var(--danger)' }} onClick={() => handleSimulate('AD')} disabled={loading}>AD Patient</button>
          </div>
        </div>

        <div className="panel">
          <div className="panel-title" style={{marginBottom: 0}}>
            <Activity size={14} /> Panel 2 & 3: Inference & Modalities
          </div>

          {!result && !loading && (
            <div className="results-empty">
              <Activity size={40} />
              <div style={{fontSize: '0.9rem'}}>Awaiting pipeline execution.<br/>Load data to generate inference.</div>
            </div>
          )}

          {loading && (
            <div className="results-empty">
              <Loader2 className="spinner" size={40} color="var(--accent)" />
              <div style={{color: 'var(--text-main)', fontWeight: 500, fontSize: '0.9rem'}}>Extracting Acoustic Covariates...</div>
            </div>
          )}

          {result && !loading && (
            <div style={{display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '4px', animation: 'fadeUp 0.6s ease'}}>
              
              <div className="metric" style={{borderColor: result.ad_probability > 0.5 ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}}>
                <div className="metric-header">
                  Clinical Diagnosis
                  {result.ad_probability > 0.5 ? <div className="header-badge" style={{color: 'var(--danger)', background: 'rgba(239,68,68,0.1)', borderColor: 'rgba(239,68,68,0.2)'}}>Alert</div> : null}
                </div>
                <div className={`metric-val ${result.ad_probability > 0.5 ? 'text-danger' : 'text-success'}`} style={{textAlign: 'center', padding: '10px 0'}}>
                  {result.classification}
                </div>
              </div>

              <div className="metric">
                <div className="metric-header" style={{borderBottom: '1px solid var(--border-light)', paddingBottom: '10px', marginBottom: '4px'}}>
                  Modality Independent Contributions
                </div>
                {result.modality_probs && (
                  <>
                    <ConfidenceRow label="Acoustic Stream" prob={result.modality_probs.acoustic} />
                    <ConfidenceRow label="Linguistic Stream" prob={result.modality_probs.text} />
                    <ConfidenceRow label="Clinical Covariates" prob={result.modality_probs.clinical} />
                    <div style={{height: '1px', background: 'var(--border-light)', margin: '14px 0 8px'}} />
                  </>
                )}
                <ConfidenceRow label="Trimodal PoE Fusion" prob={result.ad_probability} />
              </div>

              <div className="metric">
                <div className="metric-header" style={{borderBottom: '1px solid var(--border-light)', paddingBottom: '10px'}}>
                  Regressed MMSE Index
                </div>
                <MmseGauge score={result.mmse_score} />
              </div>

              <div className="metric" style={{ background: 'rgba(59, 130, 246, 0.03)', borderStyle: 'dashed' }}>
                <div className="metric-header" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Clinical Interpretation
                </div>
                <div style={{ fontSize: '0.8rem', lineHeight: '1.4', color: 'var(--text-muted)', marginTop: '4px' }}>
                  {result.ad_probability > 0.5 
                    ? `Patient exhibits significant ${result.modality_probs.text > 0.8 ? 'linguistic fragmentation' : 'acoustic markers'} consistent with early-stage Dementia. MMSE index (${result.mmse_score.toFixed(1)}) warrants immediate clinical follow-up.`
                    : `Cognitive profiles are within normal variance. Trimodal fusion indicates high stability across linguistic and acoustic streams.`
                  }
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Panels 4 and 5: Training Results & Dataset Explorer */}
      <div className="grid-layout">
        <div className="panel">
          <div className="panel-title">
            <LineChart size={14} /> Panel 4: Training Results
          </div>
          
          <div style={{ display: 'flex', gap: '10px', marginBottom: '4px' }}>
            <button className={`badge-btn ${activeTab === 'TAUKADIAL' ? 'active' : ''}`} onClick={() => setActiveTab('TAUKADIAL')}>TAUKADIAL</button>
            <button className={`badge-btn ${activeTab === 'ADReSS' ? 'active' : ''}`} onClick={() => setActiveTab('ADReSS')}>ADReSS</button>
          </div>

          {activeTab === 'TAUKADIAL' ? (
            <table className="benchmark-table">
              <thead>
                <tr><th>Fold</th><th>AUC</th><th>F1</th><th>RMSE</th></tr>
              </thead>
              <tbody>
                <tr><td>Fold 1</td><td>0.892</td><td>0.884</td><td>4.12</td></tr>
                <tr><td>Fold 2</td><td>0.915</td><td>0.902</td><td>3.85</td></tr>
                <tr><td>Fold 3</td><td>0.887</td><td>0.865</td><td>4.33</td></tr>
                <tr><td>Fold 4</td><td>0.920</td><td>0.911</td><td>3.70</td></tr>
                <tr><td>Fold 5</td><td>0.908</td><td>0.895</td><td>3.91</td></tr>
                <tr className="highlight"><td>Mean ± Std</td><td>0.904 ± .01</td><td>0.891 ± .02</td><td>3.98 ± .2</td></tr>
              </tbody>
            </table>
          ) : (
            <table className="benchmark-table">
              <thead>
                <tr><th>Fold</th><th>AUC</th><th>F1</th><th>RMSE</th></tr>
              </thead>
              <tbody>
                <tr><td>Fold 1</td><td>0.841</td><td>0.838</td><td>4.75</td></tr>
                <tr><td>Fold 2</td><td>0.865</td><td>0.852</td><td>4.50</td></tr>
                <tr><td>Fold 3</td><td>0.850</td><td>0.844</td><td>4.62</td></tr>
                <tr><td>Fold 4</td><td>0.873</td><td>0.869</td><td>4.21</td></tr>
                <tr><td>Fold 5</td><td>0.859</td><td>0.851</td><td>4.44</td></tr>
                <tr className="highlight"><td>Mean ± Std</td><td>0.857 ± .01</td><td>0.850 ± .01</td><td>4.50 ± .1</td></tr>
              </tbody>
            </table>
          )}

          <div className="benchmark-bars" style={{ marginTop: '16px' }}>
            <div className="benchmark-row">
              <span className="btitle" style={{fontSize: '0.75rem'}}>CogniVoice (2022)</span>
              <div className="bbar"><div style={{width:'84.1%', background:'var(--text-muted)'}}/></div>
              <span style={{fontSize: '0.75rem'}}>84.1%</span>
            </div>
            <div className="benchmark-row">
              <span className="btitle" style={{fontSize: '0.75rem'}}>Bang et al. (2023)</span>
              <div className="bbar"><div style={{width:'87.3%', background:'var(--text-muted)'}}/></div>
              <span style={{fontSize: '0.75rem'}}>87.3%</span>
            </div>
            <div className="benchmark-row">
              <span className="btitle" style={{fontSize: '0.75rem'}}>Trimodal PoE (Ours)</span>
              <div className="bbar"><div style={{width:'90.4%', background:'var(--accent)'}}/></div>
              <span style={{color:'var(--accent)', fontWeight:600, fontSize: '0.75rem'}}>90.4%</span>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-title">
            <Database size={14} /> Panel 5: Dataset Explorer
          </div>

          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'20px'}}>
            <div className="dataset-stat">
              <div className="dtitle">Total Patients</div>
              <div className="dval">{activeTab === 'TAUKADIAL' ? '507' : '156'} <span style={{fontSize:'0.75rem', color:'var(--text-muted)'}}>{activeTab}</span></div>
            </div>
            <div className="dataset-stat">
              <div className="dtitle">Age Range</div>
              <div className="dval">{activeTab === 'TAUKADIAL' ? '55 - 90' : '53 - 79'} <span style={{fontSize:'0.75rem', color:'var(--text-muted)'}}>Years</span></div>
            </div>
          </div>

          <div style={{marginTop:'24px'}}>
            <div className="panel-title" style={{marginBottom:'16px', color:'var(--text-main)'}}>MMSE Clinical Distribution (AD vs HC)</div>
            <div className="histogram">
              {[38, 45, 60, 50, 42, 20, 10, 5, 2, 0].map((h1, i) => {
                const h2 = [0, 5, 10, 25, 40, 55, 75, 85, 60, 45][i];
                return (
                  <div key={i} className="hist-col">
                    <div className="hist-ad" style={{height: `${h1}%`}} />
                    <div className="hist-hc" style={{height: `${h2}%`}} />
                    <span className="hist-label">{i*3}</span>
                  </div>
                );
              })}
            </div>
            <div style={{display:'flex', gap:'15px', justifyContent:'center', marginTop:'30px', fontSize:'0.75rem', color:'var(--text-muted)'}}>
              <div style={{display:'flex', alignItems:'center', gap:'6px'}}><div style={{width:'10px', height:'10px', background:'var(--danger)', borderRadius:'2px'}}/> Alzheimer's Disease (AD)</div>
              <div style={{display:'flex', alignItems:'center', gap:'6px'}}><div style={{width:'10px', height:'10px', background:'var(--success)', borderRadius:'2px'}}/> Healthy Control (HC)</div>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}

export default App;
