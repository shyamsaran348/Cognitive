import React from 'react';
import { History, ChevronRight, Clock, FileText } from 'lucide-react';

const SessionHistory = ({ history, setResult }) => {
  return (
    <aside className="panel-white animate-slide-up" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px', color: 'var(--primary)', fontWeight: 700 }}>
        <History size={18} />
        Recent Assessments
      </div>

      <div className="history-list" style={{ flex: 1, overflowY: 'auto' }}>
        {history.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <Clock size={32} style={{ opacity: 0.1, marginBottom: '12px' }} />
            <p>No previous patient history found in this session.</p>
          </div>
        ) : (
          history.map((h, i) => {
            const isHealthy = h.mmse_score >= 18;
            const statusColor = isHealthy ? 'var(--success)' : 'var(--danger)';
            const statusBg = isHealthy ? '#dcfce7' : '#fef2f2';

            return (
              <div 
                key={i} 
                className="history-item"
                style={{ 
                  border: '1px solid var(--border-light)', 
                  borderRadius: '12px', 
                  padding: '16px', 
                  marginBottom: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onClick={() => setResult(h)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <span style={{ 
                    fontSize: '0.65rem', fontWeight: 800, padding: '2px 8px', borderRadius: '4px',
                    background: statusBg, color: statusColor
                  }}>
                    {h.diagnosis || h.classification}
                  </span>
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                    {new Date(h.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700 }}>MMSE: {h.mmse_score.toFixed(1)}</div>
                  <ChevronRight size={14} color="var(--text-muted)" />
                </div>
              </div>
            );
          })
        )}
      </div>

      <div style={{ marginTop: '24px', borderTop: '1px solid var(--border-light)', paddingTop: '20px' }}>
         <button className="btn-outline" style={{ width: '100%', fontSize: '0.75rem', padding: '10px' }}>
           View Full Database
         </button>
      </div>
    </aside>
  );
};

export default SessionHistory;
