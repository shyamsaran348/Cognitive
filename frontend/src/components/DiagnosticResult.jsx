import React from 'react';
import { 
  CheckCircle2, AlertCircle, Shield, Activity, 
  Brain, FileText, ChevronRight, Info, Zap, 
  ShieldCheck, AlertTriangle, Eye, ArrowRight
} from 'lucide-react';

/**
 * DiagnosticResult — Displays the final AI-fused clinical report.
 * V2.5: Multi-battery aware (ACE-III + MoCA + Passive Voice).
 */
const DiagnosticResult = ({ result, activeResults }) => {
  if (!result) return null;

  const statusColor = result.risk_level.includes('Healthy') ? '#10b981' : 
                      result.risk_level.includes('Possible AD') ? '#fbbf24' : '#ef4444';
  const statusBg = `${statusColor}15`;
  const breakdown = result.modality_breakdown || {};
  const timestamp = new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });

  // Helper to find score in any active battery
  const getDomainScore = (key) => {
    if (!activeResults) return 0;
    // activeResults is now { ace3: {...}, moca: {...} } or { cogni: {...} }
    for (const battery of Object.values(activeResults)) {
      if (battery[key]) return battery[key].score;
    }
    return 0;
  };

  const generateClinicalPDF = () => {
    const html = `
      <!DOCTYPE html><html><head><title>CogniSense Clinical Report</title>
      <style>
        body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #1a1a2e; margin: 0; padding: 40px; font-size: 12px; }
        h1 { font-size: 22px; font-weight: 900; color: #1a1a2e; margin-bottom: 4px; }
        h2 { font-size: 14px; font-weight: 700; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin: 24px 0 12px; }
        .header { background: #0f172a; color: white; padding: 28px 36px; margin: -40px -40px 32px; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
        .badge-green { background: #d1fae5; color: #065f46; }
        .badge-red { background: #fee2e2; color: #991b1b; }
        .badge-yellow { background: #fef3c7; color: #92400e; }
        .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; }
        .mmse-big { font-size: 56px; font-weight: 900; color: #0f172a; line-height: 1; }
        .note { font-size: 11px; color: #64748b; line-height: 1.6; padding: 10px 14px; background: #f8fafc; border-radius: 8px; margin-bottom: 6px; font-style: italic; }
        .domain-row { display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding: 6px 0; font-size: 11px; }
        .progress { height: 4px; background: #e2e8f0; border-radius: 2px; overflow: hidden; margin-top: 4px; }
        .progress-fill { height: 100%; background: #6366f1; border-radius: 2px; }
        .footer { margin-top: 40px; font-size: 9px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 12px; }
        @media print { body { padding: 20px; } .header { margin: -20px -20px 24px; } }
      </style></head><body>
      <div class="header">
        <h1>Integrated Clinical Summary</h1>
        <div style="margin-top:8px;font-size:11px;opacity:0.7">CogniSense Bayesian Fusion v2.45 • Generated: ${timestamp}</div>
      </div>

      <div class="grid2">
        <div class="card">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#64748b;margin-bottom:8px">Integrated Diagnostic Index</div>
          <div class="mmse-big">${result.mmse_score ?? 'N/A'}</div>
          <div style="font-size:11px;color:#64748b;margin-top:4px">/ 30.0 — ${result.diagnosis}</div>
          <span class="badge ${result.risk_level === 'Healthy' ? 'badge-green' : result.risk_level === 'Moderate Risk' ? 'badge-yellow' : 'badge-red'}" style="margin-top:12px">${result.risk_level}</span>
        </div>
        <div class="card">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#64748b;margin-bottom:8px">Evidence Synthesis Breakdown</div>
          ${Object.values(breakdown).map(m => `
            <div class="domain-row">
              <span>${m.label}</span>
              <span><b>${m.score}</b> (Conf: ${Math.round(m.confidence * 100)}%) · Contrib: ${m.contribution}</span>
            </div>
          `).join('')}
          <div class="domain-row" style="margin-top:8px; border-top: 1px solid #000; font-weight:700">
            <span>Integrated Consensus</span>
            <span>${result.agreement_icon || ''} ${result.agreement}</span>
          </div>
        </div>
      </div>

      <h2>Multi-Modality Domain Performance</h2>
      <div class="grid2">
        ${[
          ['Memory – Registration', 'memory', 3],
          ['Memory – Recall', 'recall', 3],
          ['Language – Repeat', 'language_repeat', 5],
          ['Language – Naming', 'language_naming', 6],
          ['Fluency – Semantic', 'fluency', 10],
          ['Executive – Abstract', 'executive_abstract', 4],
          ['Attention – Digits', 'attention_digits', 5],
          ['Attention – Serial 7s', 'attention_serial7', 5],
          ['Orientation – Time', 'orientation_time', 3],
          ['Orientation – Place', 'orientation_place', 3],
        ].map(([label, key, max]) => {
          const score = getDomainScore(key);
          return `
            <div class="card">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-weight:600">${label}</span>
                <span><b>${score ?? 0}</b> / ${max}</span>
              </div>
              <div class="progress"><div class="progress-fill" style="width:${((score ?? 0) / max * 100).toFixed(0)}%"></div></div>
            </div>
          `;
        }).join('')}
      </div>

      <h2>Qualitative Clinical Observations</h2>
      <div class="note">${(result.clinical_narrative || "No specific deviations detected.").replace(/\n/g, '<br/>')}</div>

      <h2>Expert Integration Rationale</h2>
      <div class="note">${result.agreement_detail || 'Consensus logic applied across all modalities.'}</div>

      <div class="footer">
        ⚠️ This report is generated by an AI-assisted diagnostic instrument. Final diagnosis remains the sole responsibility of the clinician. Distributed for private clinical review only.
      </div>
      <script>window.onload = () => window.print();</script>
      </body></html>
    `;
    const w = window.open('', '_blank', 'width=900,height=700');
    w.document.write(html);
    w.document.close();
  };

  return (
    <div className="diagnostic-synthesis animate-slide-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div className="badge-green">Integrated Clinical Evaluation v2.45</div>
        <div className="badge-blue" style={{ background: 'var(--primary-light)', color: 'white', padding: '4px 12px', borderRadius: '20px', fontSize: '0.7rem', fontWeight: 800 }}>
          <CheckCircle2 size={12} style={{ marginRight: '4px' }} /> Sequential Multi-Battery Active Verification
        </div>
      </div>
      
      <h2 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Integrated Multimodal Consensus</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '32px', fontSize: '0.9rem' }}>
        Synthesized Patient State • Bayesian Consensus Layer
      </p>

      {/* High-Level Evidence Panels */}
      <div style={{ marginBottom: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
        {/* Consensus Quality */}
        <div style={{ padding: '20px', background: 'var(--bg-secondary)', borderRadius: '16px', border: '1px solid var(--border-light)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>Integrated Agreement</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <span style={{ fontSize: '1.5rem' }}>{result.agreement_icon}</span>
            <span style={{
              fontWeight: 800, fontSize: '1.1rem',
              color: result.agreement === 'High' ? '#10b981' : result.agreement === 'Moderate' ? '#f59e0b' : '#ef4444'
            }}>{result.agreement}</span>
          </div>
          <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
            {result.agreement_detail}
          </p>
        </div>

        {/* Modality Contribution Chart */}
        <div style={{ padding: '20px', background: 'var(--bg-secondary)', borderRadius: '16px', border: '1px solid var(--border-light)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '12px' }}>Modality Weighting</div>
          {Object.entries(breakdown).map(([id, m], i) => (
            <div key={id} style={{ marginBottom: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                <span style={{ fontWeight: 600 }}>{m.label}</span>
                <span style={{ fontWeight: 800 }}>{m.contribution}</span>
              </div>
              <div style={{ height: '6px', background: 'rgba(0,0,0,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ 
                  width: m.contribution, height: '100%', 
                  background: id === 'passive' ? 'var(--primary)' : id === 'ace3' ? '#10b981' : '#f59e0b', 
                  borderRadius: '3px' 
                }} />
              </div>
            </div>
          ))}
        </div>

        {/* Fusion Confidence */}
        <div style={{ padding: '20px', background: 'var(--primary-light)', color: 'white', borderRadius: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ fontSize: '0.7rem', opacity: 0.8, textTransform: 'uppercase', marginBottom: '8px' }}>Bayesian Confidence</div>
          <div style={{ fontSize: '2.8rem', fontWeight: 900, lineHeight: 1 }}>{Math.round(result.confidence * 100)}%</div>
          <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '8px', textAlign: 'center' }}>
            Evidence Strength: {result.assessment_quality}
          </div>
        </div>
      </div>

      <div className="synthesis-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Verdict Panel */}
          <div className="panel-white" style={{ borderTop: `6px solid ${statusColor}` }}>
             <h4 style={{ margin: '0 0 16px', fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Clinical Conclusion</h4>
             <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                   <div style={{ 
                     padding: '8px 20px', borderRadius: '40px', background: statusBg, color: statusColor,
                     fontSize: '1.4rem', fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: '8px'
                   }}>
                      {result.mmse_score >= 26 ? <ShieldCheck size={24} /> : <AlertTriangle size={24} />}
                      {result.risk_level}
                   </div>
                   <p style={{ marginTop: '12px', fontSize: '0.95rem', fontWeight: 700 }}>{result.diagnosis}</p>
                </div>
                <div style={{ textAlign: 'right' }}>
                   <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Fused MMSE</div>
                   <div style={{ fontSize: '3.2rem', fontWeight: 900, lineHeight: 1 }}>{result.mmse_score.toFixed(1)}</div>
                </div>
             </div>
          </div>

          {/* Combined Domain Performance */}
          <div className="panel-white">
             <h4 style={{ margin: '0 0 20px', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
               <Activity size={16} color="var(--primary)" /> Integrated Domain compass
             </h4>
             <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                {[
                  { domain: 'Memory', key: 'memory', total: 3, label: 'Registration' },
                  { domain: 'Recall', key: 'recall', total: 3, label: 'Delayed Recall' },
                  { domain: 'Language', key: 'language_repeat', total: 5, label: 'Repetition' },
                  { domain: 'Fluency', key: 'fluency', total: 10, label: 'Semantic' },
                  { domain: 'Executive', key: 'executive_abstract', total: 4, label: 'Abstract' },
                  { domain: 'Attention', key: 'attention_digits', total: 5, label: 'Digit Span' },
                ].map((row, i) => {
                  const score = getDomainScore(row.key);
                  return (
                    <div key={i} style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-light)' }}>
                       <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{row.domain}</div>
                       <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '8px' }}>
                          <span style={{ fontWeight: 800, fontSize: '1.2rem' }}>{score}<span style={{ fontSize: '0.8rem', opacity: 0.5 }}>/{row.total}</span></span>
                          <span style={{ fontSize: '0.65rem', fontWeight: 600 }}>{row.label}</span>
                       </div>
                       <div style={{ height: '3px', background: 'rgba(0,0,0,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{ width: `${(score / row.total) * 100}%`, height: '100%', background: 'var(--primary)', borderRadius: '2px' }} />
                       </div>
                    </div>
                  );
                })}
             </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Narrative Observations */}
          <div className="panel-white" style={{ borderLeft: '4px solid var(--primary)', flex: 1 }}>
             <h4 style={{ margin: '0 0 16px', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
               <Brain size={16} color="var(--primary)" /> Qualitative Insights
             </h4>
             <div style={{ fontSize: '0.85rem', lineHeight: '1.6', whiteSpace: 'pre-line' }}>
                {result.clinical_narrative || "The integrated cognitive profile suggests baseline stability across active and passive modalities."}
             </div>
             
             {result.failure_modes && result.failure_modes.length > 0 && (
               <div style={{ marginTop: '20px', padding: '12px', background: '#fffbeb', borderRadius: '8px', border: '1px solid #fef3c7' }}>
                 <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#92400e', marginBottom: '6px' }}>Quality Warnings:</div>
                 {result.failure_modes.map((f, i) => (
                   <div key={i} style={{ fontSize: '0.7rem', color: '#b45309' }}>• {f.message}</div>
                 ))}
               </div>
             )}
          </div>

          <button className="btn-primary" onClick={generateClinicalPDF} style={{ width: '100%', padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <FileText size={20} /> Download Sequential Clinical Report (PDF)
          </button>
        </div>
      </div>
    </div>
  );
};

export default DiagnosticResult;
