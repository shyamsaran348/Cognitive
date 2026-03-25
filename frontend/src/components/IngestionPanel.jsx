import React from 'react';
import { Upload, CheckCircle2, Activity, Play, Loader2, Mic, ImageIcon, Info } from 'lucide-react';
import cookieTheft from '../assets/cookie_theft.jpeg';

const IngestionPanel = ({ 
  file, handleFileChange, isRecording, startRecording, stopRecording, 
  liveWaveform, result, Waveform, LiveWaveform, loading, steps, StepTracker,
  age, setAge, education, setEducation, cdr, setCdr, handleAnalyze,
  hideMetadata = false, onBack
}) => {
  return (
    <div className="panel-white animate-slide-up" style={{ maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
        <div>
          <div className="badge-green"><Activity size={14} /> Stage 3: Audio Ingestion</div>
          <h3 style={{ margin: '8px 0 4px' }}>Speech Biomarker Capture</h3>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)' }}>Upload or record patient voice for Trimodal analysis.</p>
        </div>
      </div>

      <div style={{ padding: '24px', background: '#f8fafc', borderRadius: '16px', border: '1px solid #e2e8f0', marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <ImageIcon size={18} color="var(--primary)" />
          <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#1e293b' }}>Standard Clinical Elicitation (Cookie Theft)</span>
        </div>
        <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
          <div style={{ flex: '0 0 240px', height: '180px', background: '#f1f5f9', borderRadius: '12px', overflow: 'hidden', border: '1px solid #cbd5e1' }}>
            <img 
              src={cookieTheft} 
              alt="Cookie Theft Clinical Task" 
              style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
              onError={(e) => { e.target.style.display='none'; e.target.parentNode.innerHTML='<div style="height:100%;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:0.7rem">Image asset missing</div>'; }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ background: 'var(--primary-light)', color: 'white', padding: '16px', borderRadius: '12px', fontSize: '0.95rem', lineHeight: '1.5', fontWeight: 500, position: 'relative' }}>
              "Please describe everything you see happening in this picture. Take your time to include all details."
              <div style={{ position: 'absolute', left: '-8px', top: '20px', width: 0, height: 0, borderTop: '8px solid transparent', borderBottom: '8px solid transparent', borderRight: '8px solid var(--primary-light)' }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px', color: '#64748b', fontSize: '0.75rem' }}>
              <Info size={14} /> 
              Expected response: ~2-3 minutes of spontaneous speech.
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '32px' }}>
        <div 
          className={`upload-zone ${file ? 'active' : ''}`}
          style={{ 
            border: '2px dashed var(--border-light)', 
            padding: '40px', 
            borderRadius: '16px', 
            textAlign: 'center', 
            cursor: 'pointer',
            background: file ? 'var(--accent)' : 'var(--bg-secondary)',
            transition: 'all 0.2s'
          }}
          onClick={() => document.getElementById('audio-upload').click()}
        >
          <input type="file" id="audio-upload" hidden onChange={handleFileChange} accept="audio/*" />
          {file ? <CheckCircle2 size={32} color="var(--primary)" /> : <Upload size={32} color="var(--text-muted)" />}
          <p style={{ margin: '16px 0 0', fontSize: '0.9rem', fontWeight: 600 }}>{file ? file.name : 'Select Audio File'}</p>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>WAV preferred (16kHz Mono)</span>
        </div>

        <div 
          className={`recorder-zone ${isRecording ? 'recording' : ''}`}
          style={{ 
            border: '1px solid var(--border-light)', 
            padding: '40px', 
            borderRadius: '16px', 
            textAlign: 'center', 
            cursor: 'pointer',
            background: isRecording ? '#fef2f2' : 'var(--white)',
            transition: 'all 0.2s'
          }}
          onClick={isRecording ? stopRecording : startRecording}
        >
          <div style={{ 
            width: '48px', height: '48px', borderRadius: '50%', background: isRecording ? 'var(--danger)' : 'var(--bg-secondary)', 
            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px',
            color: isRecording ? 'white' : 'var(--primary)',
            boxShadow: isRecording ? '0 0 15px rgba(239, 68, 68, 0.4)' : 'none'
          }}>
            <Mic size={24} />
          </div>
          <p style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600 }}>{isRecording ? 'Stop Recording' : 'Live Microphone'}</p>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Real-time capture</span>
        </div>
      </div>

      {loading && (
        <div style={{ margin: '32px 0', padding: '24px', background: 'var(--bg-secondary)', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', color: 'var(--primary)', fontWeight: 700 }}>
             <Loader2 size={18} className="spinner" /> 
             <span>Analyzing Neural Stream...</span>
          </div>
          {/* Step Tracker Placeholder */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {steps.map(s => (
              <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', opacity: s.status === 'pending' ? 0.4 : 1 }}>
                {s.status === 'done' ? <CheckCircle2 size={14} color="var(--success)" /> : <div style={{ width: '14px', height: '14px', border: '1.5px solid currentColor', borderRadius: '50%' }} />}
                {s.label}
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: '16px', marginTop: '40px' }}>
        <button 
          className="btn-primary" 
          onClick={handleAnalyze} 
          disabled={!file || loading} 
          style={{ flex: 1, padding: '18px' }}
        >
          {loading ? <Loader2 className="spinner" /> : <Play size={18} fill="currentColor" />}
          {loading ? 'Processing Biomarkers...' : 'Record & Begin Inference'}
        </button>
        <button className="btn-outline" onClick={onBack}>Back</button>
      </div>
    </div>
  );
};

export default IngestionPanel;
