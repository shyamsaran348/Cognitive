import React from 'react';
import { Brain, CheckCircle2, Shield, Activity, ArrowRight, ClipboardCheck, Loader2, AlertCircle } from 'lucide-react';

const ConsensusReviewScreen = ({ 
  passiveReady, 
  activeReady, 
  passiveData,
  activeData,
  onFinalize, 
  onNavigate, // NEW: Handle navigation back to tests
  isLoading, 
  error 
}) => {
  const allReady = passiveReady && activeReady;

  // Calculate aggregated active score
  const activeScore = activeData ? Object.values(activeData).reduce((sum, res) => sum + (res.score || 0), 0) : 0;
  const activeMax = 100; // Simplified max for clinical battery

  return (
    <div className="consensus-review animate-slide-up" style={{ padding: '40px', background: 'white', borderRadius: '24px', boxShadow: '0 20px 40px rgba(0,0,0,0.05)', textAlign: 'center' }}>
      <div style={{ display: 'inline-flex', padding: '16px', background: 'var(--primary-light)', borderRadius: '20px', color: 'white', marginBottom: '24px' }}>
        <Shield size={32} />
      </div>
      
      <h2 style={{ fontSize: '2rem', marginBottom: '12px' }}>Final Clinical Quality Review</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '40px' }}>
        Assessment phase complete. Please review the signal status before generating the final diagnostic consensus.
      </p>

      {error && (
        <div style={{ padding: '16px', background: '#fef2f2', border: '1px solid #fee2e2', borderRadius: '12px', color: '#b91c1c', marginBottom: '32px', display: 'flex', alignItems: 'center', gap: '12px', textAlign: 'left' }}>
          <AlertCircle size={20} />
          <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{error}</span>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '48px' }}>
        {/* Passive Marker Card */}
        <div 
          onClick={() => onNavigate('passive')}
          className="consensus-card"
          style={{ 
            padding: '24px', background: 'var(--bg-secondary)', borderRadius: '20px', 
            border: `2px solid ${passiveReady ? '#10b981' : 'var(--border-light)'}`,
            cursor: 'pointer', transition: 'all 0.3s ease',
            position: 'relative', overflow: 'hidden'
          }}
        >
          <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'center' }}>
            {passiveReady ? <CheckCircle2 color="#10b981" size={28} /> : <Activity className="animate-pulse" color="var(--primary)" size={28} />}
          </div>
          <div style={{ fontWeight: 800, fontSize: '0.95rem' }}>Passive Voice Markers</div>
          <div style={{ fontSize: '0.75rem', color: passiveReady ? '#059669' : 'var(--text-muted)', marginTop: '8px', fontWeight: 600 }}>
            {passiveReady ? `Verified (MMSE: ${Math.round(passiveData?.mmse_prediction || 0)})` : 'Click to Record Audio'}
          </div>
          {!passiveReady && (
            <div style={{ position: 'absolute', right: '12px', bottom: '12px', opacity: 0.3 }}>
              <ArrowRight size={16} />
            </div>
          )}
        </div>

        {/* Active Clinical Battery Card */}
        <div 
          onClick={() => onNavigate('active')}
          className="consensus-card"
          style={{ 
            padding: '24px', background: 'var(--bg-secondary)', borderRadius: '20px', 
            border: `2px solid ${activeReady ? '#10b981' : 'var(--border-light)'}`,
            cursor: 'pointer', transition: 'all 0.3s ease',
            position: 'relative', overflow: 'hidden'
          }}
        >
          <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'center' }}>
            {activeReady ? <CheckCircle2 color="#10b981" size={28} /> : <Activity className="animate-pulse" color="var(--primary)" size={28} />}
          </div>
          <div style={{ fontWeight: 800, fontSize: '0.95rem' }}>Active Clinical Battery</div>
          <div style={{ fontSize: '0.75rem', color: activeReady ? '#059669' : 'var(--text-muted)', marginTop: '8px', fontWeight: 600 }}>
            {activeReady ? `Verified (Battery Score: ${Math.round(activeScore)})` : 'Click to Begin Battery'}
          </div>
          {!activeReady && (
            <div style={{ position: 'absolute', right: '12px', bottom: '12px', opacity: 0.3 }}>
              <ArrowRight size={16} />
            </div>
          )}
        </div>
      </div>

      <div style={{ padding: '24px', background: '#f8fafc', borderRadius: '16px', border: '1px solid #e2e8f0', marginBottom: '40px', textAlign: 'left' }}>
        <div style={{ display: 'flex', gap: '12px' }}>
          <Info size={20} color="var(--primary)" />
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#1e293b' }}>Unified Bayesian Fusion Protocol</div>
            <p style={{ margin: '4px 0 0', fontSize: '0.75rem', color: '#64748b', lineHeight: '1.5' }}>
              The engine will synthesize passive acoustic biomarkers with the unified clinical battery performance. 
              Weights are dynamically calibrated to account for signal reliability and cognitive load variance.
            </p>
          </div>
        </div>
      </div>

      <button 
        className="btn-primary" 
        onClick={onFinalize}
        disabled={!allReady || isLoading}
        style={{ width: '100%', padding: '20px', fontSize: '1.1rem', gap: '12px', opacity: (allReady && !isLoading) ? 1 : 0.7 }}
      >
        {isLoading ? <Loader2 className="animate-spin" size={24} /> : <Brain size={24} />} 
        {isLoading ? 'Synthesizing Consensus...' : 'Generate Integrated Clinical Consensus'} 
        {!isLoading && <ArrowRight size={20} />}
      </button>

      {!allReady && !isLoading && (
        <p style={{ marginTop: '24px', fontSize: '0.85rem', color: '#ef4444', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
          <AlertCircle size={16} /> Please complete both markers to generate the final diagnostic consensus.
        </p>
      )}
    </div>
  );
};

const Info = ({ size, color }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>
  </svg>
);

export default ConsensusReviewScreen;
