import React from 'react';
import { ArrowRight, Play, Shield, Activity, Database, CheckCircle2 } from 'lucide-react';

const WelcomeScreen = ({ onStart }) => {
  return (
    <div className="welcome-page animate-slide-up">
      {/* Hero Section */}
      <section className="hero-grid">
        <div className="hero-content">
          <div className="badge-green">
             <div style={{ width: '8px', height: '8px', background: 'var(--primary)', borderRadius: '50%' }} />
             AI-Powered Cognitive Assessment
          </div>
          <h1>Early detection of <span style={{ fontStyle: 'italic', fontWeight: '400' }}>cognitive decline</span> from speech</h1>
          <p>
            CogniSense analyses acoustic patterns, linguistic markers, and clinical context to support early diagnosis of Alzheimer’s Disease and Mild Cognitive Impairment.
          </p>
          <div style={{ display: 'flex', gap: '16px' }}>
            <button className="btn-primary" onClick={onStart} style={{ padding: '16px 32px', fontSize: '1rem' }}>
              Start Assessment <ArrowRight size={20} />
            </button>
            <button className="btn-outline" style={{ padding: '16px 32px', fontSize: '1rem' }}>Explore Test Hub</button>
          </div>
        </div>

        <div className="hero-visual">
          <div className="stream-card">
            <div className="stream-icon"><Activity size={24} /></div>
            <div>
              <h4 style={{ margin: '0 0 4px', fontSize: '0.9rem' }}>Acoustic Streaming</h4>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>Wav2vec 2.0 & eGeMAPS e-biomarkers</p>
            </div>
          </div>
          <div className="stream-card" style={{ marginLeft: '40px' }}>
            <div className="stream-icon" style={{ background: '#fdf2f8', color: '#db2777' }}><Shield size={24} /></div>
            <div>
              <h4 style={{ margin: '0 0 4px', fontSize: '0.9rem' }}>Linguistic Markers</h4>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>RoBERTa-large semantic vectorization</p>
            </div>
          </div>
          <div className="stream-card">
            <div className="stream-icon" style={{ background: '#eff6ff', color: '#2563eb' }}><Database size={24} /></div>
            <div>
              <h4 style={{ margin: '0 0 4px', fontSize: '0.9rem' }}>Clinical Data</h4>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>Bayesian patient context integration</p>
            </div>
          </div>
        </div>
      </section>

      {/* Workflow Section */}
      <section className="workflow-section">
        <div className="badge-green" style={{ marginBottom: '16px' }}>Workflow</div>
        <h2 style={{ fontSize: '2.5rem', marginBottom: '40px' }}>How it works</h2>
        
        <div className="workflow-grid">
          <div className="workflow-item">
            <div className="workflow-num">01</div>
            <h5>Patient Intake</h5>
            <p>Enter age, education level, and CDR score to calibrate clinical baseline.</p>
          </div>
          <div className="workflow-item">
            <div className="workflow-num">02</div>
            <h5>Upload Audio</h5>
            <p>Upload a voice recording — ideally a Cookie Theft picture description task.</p>
          </div>
          <div className="workflow-item">
            <div className="workflow-num">03</div>
            <h5>Trimodal Analysis</h5>
            <p>Three AI experts analyse acoustic, linguistic, and clinical signals simultaneously.</p>
          </div>
          <div className="workflow-item">
            <div className="workflow-num">04</div>
            <h5>PoE Fusion</h5>
            <p>Product of Experts merges outputs, weighting reliable modalities more heavily.</p>
          </div>
          <div className="workflow-item">
            <div className="workflow-num">05</div>
            <h5>Diagnostic Report</h5>
            <p>Receive MMSE prediction, risk tier breakdown, and per-expert clinical notes.</p>
          </div>
        </div>
      </section>

      {/* Trust Badge */}
      <section style={{ padding: '80px', textAlign: 'center', borderTop: '1px solid var(--border-light)' }}>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '24px' }}>
          Trained on Clinical Corpora
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '60px', opacity: 0.6 }}>
           <div style={{ fontWeight: 800, fontSize: '1.2rem' }}>ADReSS 2020</div>
           <div style={{ fontWeight: 800, fontSize: '1.2rem' }}>DementiaBank / Pitt</div>
           <div style={{ fontWeight: 800, fontSize: '1.2rem' }}>TAUKADIAL</div>
        </div>
      </section>
    </div>
  );
};

export default WelcomeScreen;
