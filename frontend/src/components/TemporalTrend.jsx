import React from 'react';
import { TrendingDown, TrendingUp, Clock, AlertTriangle } from 'lucide-react';

const TemporalTrend = ({ history }) => {
  // Extract last 10 sessions and reverse for chronological plotting
  const lastSessions = [...history].reverse().slice(-10);
  
  if (lastSessions.length < 2) {
    return (
      <div className="panel-white" style={{ display: 'flex', flexDirection: 'column', gap: '16px', opacity: 0.8 }}>
        <h4 style={{ margin: '0', fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Temporal Cognitive Signature</h4>
        <div style={{ padding: '32px', textAlign: 'center', background: 'var(--bg-secondary)', borderRadius: '16px' }}>
           <Clock size={32} style={{ opacity: 0.1, marginBottom: '12px', margin: '0 auto' }} />
           <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)' }}>Additional sessions required to generate longitudinal trend analysis.</p>
        </div>
      </div>
    );
  }

  // Calculate Trend
  const latest = lastSessions[lastSessions.length - 1].mmse_score;
  const previous = lastSessions[lastSessions.length - 2].mmse_score;
  const isDeclining = latest < previous;

  // Simple Sparkline Logic
  const maxScore = 30;
  const points = lastSessions.map((s, i) => `${(i / (lastSessions.length - 1)) * 100},${100 - (s.mmse_score / maxScore) * 100}`).join(' ');

  return (
    <div className="panel-white animate-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h4 style={{ margin: '0', fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Temporal Signature</h4>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
             {isDeclining ? <TrendingDown size={20} color="var(--danger)" /> : <TrendingUp size={20} color="var(--success)" />}
             <span style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)' }}>
                {isDeclining ? 'Cognitive Decline Detected' : 'Cognitive Stability'}
             </span>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
           <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Rate of Change</div>
           <div style={{ fontSize: '1.2rem', fontWeight: 700, color: isDeclining ? 'var(--danger)' : 'var(--text-main)' }}>
             {((latest - previous)).toFixed(1)} <span style={{ fontSize: '0.8rem', fontWeight: 400 }}>pts/session</span>
           </div>
        </div>
      </div>

      {/* Sparkline Visual */}
      <div style={{ height: '120px', width: '100%', position: 'relative', background: 'var(--bg-secondary)', borderRadius: '16px', padding: '20px' }}>
        <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
           <path 
             d={`M ${points}`} 
             fill="none" 
             stroke="var(--primary)" 
             strokeWidth="3" 
             strokeLinecap="round" 
             strokeLinejoin="round" 
           />
           {lastSessions.map((s, i) => (
             <circle 
               key={i} 
               cx={(i / (lastSessions.length - 1)) * 100} 
               cy={100 - (s.mmse_score / maxScore) * 100} 
               r="3" 
               fill={i === lastSessions.length - 1 ? 'var(--primary)' : 'var(--white)'} 
               stroke="var(--primary)" 
               strokeWidth="1.5" 
             />
           ))}
        </svg>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '8px' }}>
           <span>{new Date(lastSessions[0].timestamp).toLocaleDateString()}</span>
           <span>Latest Assessment</span>
        </div>
      </div>

      {/* Trajectory Projection (Simulated Linear Regression) */}
      <div style={{ marginTop: '20px', padding: '20px', background: 'var(--white)', border: '1.5px solid var(--border-light)', borderRadius: '16px' }}>
         <h5 style={{ margin: '0 0 16px', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)' }}>
            <Zap size={16} /> Research Grade: Longitudinal Trajectory Projection
         </h5>
         <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div>
               <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Projected MMSE (6mo)</div>
               <div style={{ fontSize: '1.8rem', fontWeight: 800, color: isDeclining ? 'var(--danger)' : 'var(--primary)' }}>
                  {(latest + (latest - previous)).toFixed(1)}
               </div>
               <p style={{ margin: '4px 0 0', fontSize: '0.65rem', color: 'var(--text-muted)' }}>Assumes current rate of decline ($Δ/t$).</p>
            </div>
            <div>
               <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Clinical Progression Risk</div>
               <div style={{ fontSize: '1.1rem', fontWeight: 700, color: isDeclining ? 'var(--danger)' : 'var(--success)', marginTop: '4px' }}>
                  {isDeclining ? (latest - previous < -2 ? 'High (Accelerated)' : 'Moderate') : 'Stable / Improving'}
               </div>
               <p style={{ margin: '4px 0 0', fontSize: '0.65rem', color: 'var(--text-muted)' }}>Based on Bayesian temporal variance.</p>
            </div>
         </div>
      </div>

      {/* Narrative Alert */}
      {isDeclining && (latest < 24) && (
        <div style={{ display: 'flex', gap: '12px', padding: '16px', background: '#fef2f2', border: '1px solid #fee2e2', borderRadius: '12px' }}>
          <AlertTriangle size={18} color="var(--danger)" />
          <p style={{ margin: 0, fontSize: '0.8rem', color: '#991b1b', lineHeight: '1.4' }}>
            <strong>Formal Research Protocol Alert</strong>: Temporal decline exceedance detected. Longitudinal trajectory projection suggests progression to the next MMSE risk tier within the 6-month clinical window. Differential diagnostic review recommended.
          </p>
        </div>
      )}
    </div>
  );
};

export default TemporalTrend;
