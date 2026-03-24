import React from 'react';
import { Users, AlertTriangle, CheckCircle2, TrendingUp } from 'lucide-react';

const ClinicalSummary = ({ history }) => {
  if (!history || history.length === 0) return null;

  const total = history.length;
  const highRisk = history.filter(s => s.mmse_score < 21).length;
  const mildRisk = history.filter(s => s.mmse_score >= 21 && s.mmse_score < 27).length;
  const healthy = history.filter(s => s.mmse_score >= 27).length;

  return (
    <div className="clinical-summary animate-slide-up stagger-1" style={{ marginTop: '48px', padding: '32px', background: 'var(--white)', borderRadius: '24px', border: '1px solid var(--border-light)' }}>
      <h4 style={{ margin: '0 0 24px', fontSize: '1rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '12px' }}>
        <TrendingUp size={20} color="var(--primary)" /> Physician's Population Insights
      </h4>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '24px' }}>
        <div style={{ padding: '20px', background: 'var(--bg-secondary)', borderRadius: '16px' }}>
           <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <Users size={16} /> Total Assessed
           </div>
           <div style={{ fontSize: '2rem', fontWeight: 800 }}>{total}</div>
        </div>

        <div style={{ padding: '20px', background: 'rgba(74, 222, 128, 0.1)', borderRadius: '16px' }}>
           <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', fontSize: '0.8rem', color: '#166534' }}>
              <CheckCircle2 size={16} /> Healthy Baseline
           </div>
           <div style={{ fontSize: '2rem', fontWeight: 800, color: '#166534' }}>{healthy}</div>
        </div>

        <div style={{ padding: '20px', background: 'rgba(251, 191, 36, 0.1)', borderRadius: '16px' }}>
           <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', fontSize: '0.8rem', color: '#92400e' }}>
              <AlertTriangle size={16} /> MCI Concern
           </div>
           <div style={{ fontSize: '2rem', fontWeight: 800, color: '#92400e' }}>{mildRisk}</div>
        </div>

        <div style={{ padding: '20px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '16px' }}>
           <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', fontSize: '0.8rem', color: '#991b1b' }}>
              <AlertTriangle size={16} /> High Risk
           </div>
           <div style={{ fontSize: '2rem', fontWeight: 800, color: '#991b1b' }}>{highRisk}</div>
        </div>
      </div>
      
      <p style={{ marginTop: '24px', fontSize: '0.7rem', color: 'var(--text-muted)', textAlign: 'center' }}>
        Clinical insights derived from the last {total} trimodal Bayesian assessments.
      </p>
    </div>
  );
};

export default ClinicalSummary;
