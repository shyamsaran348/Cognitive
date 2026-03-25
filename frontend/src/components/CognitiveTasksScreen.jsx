import React from 'react';
import { FileText, Layout, ArrowLeft, Mic, ChevronRight } from 'lucide-react';

const CognitiveTasksScreen = ({ onSelectTest, onBack }) => {
  const tests = [
    {
      id: 'voice',
      title: 'Voice Analysis',
      subtitle: 'Trimodal Speech Assessment',
      desc: 'Upload a voice recording for acoustic, linguistic, and clinical analysis using our trained PoE model.',
      status: 'Live',
      active: true,
      tags: ['Language', 'Fluency', 'Prosody', 'Semantics']
    },
    {
      id: 'ace3',
      title: 'Active Clinical Battery',
      subtitle: "Comprehensive Voice-Driven Cognitive Probe",
      desc: 'Unified 10-task assessment covering Attention, Memory, Verbal Fluency, Language, and Visuospatial domains.',
      status: 'Live',
      active: true,
      tags: ['Attention', 'Memory', 'Fluency', 'Language', 'Visuospatial']
    }
  ];

  return (
    <div className="tasks-page animate-slide-up">
      <div style={{ marginBottom: '48px' }}>
        <div className="badge-green" style={{ marginBottom: '16px' }}>Assessment Suite</div>
        <h2 style={{ fontSize: '3rem', margin: '0 0 20px' }}>Clinical Assessment Hub</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem', maxWidth: '800px' }}>
          Complementary diagnostic pathways — each feeds into the final Bayesian fusion alongside your voice analysis.
        </p>
      </div>

      <div className="test-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px' }}>
        {tests.map(test => (
          <div
            key={test.id}
            className="panel-white"
            style={{
              display: 'flex', flexDirection: 'column', gap: '16px',
              cursor: 'pointer', transition: 'transform 0.2s, box-shadow 0.2s'
            }}
            onClick={() => onSelectTest(test.id)}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.08)'; }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = ''; }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div className="stream-icon" style={{ background: 'var(--accent)' }}>
                {test.id === 'voice' ? <Mic size={20} /> : <FileText size={20} />}
              </div>
              <div style={{ fontSize: '0.6rem', padding: '4px 8px', borderRadius: '4px', fontWeight: 800, background: '#dcfce7', color: '#166534' }}>
                {test.status}
              </div>
            </div>

            <div>
              <h4 style={{ margin: '0 0 4px', fontSize: '1.1rem' }}>{test.title}</h4>
              <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--text-muted)' }}>{test.subtitle}</p>
            </div>

            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.5', flex: 1 }}>
              {test.desc}
            </p>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {test.tags.map(tag => (
                <span key={tag} style={{ fontSize: '0.65rem', padding: '2px 8px', background: 'var(--bg-secondary)', borderRadius: '4px', color: 'var(--text-muted)' }}>{tag}</span>
              ))}
            </div>

            <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)', fontWeight: 700, fontSize: '0.9rem' }}>
              Open Assessment <ChevronRight size={16} />
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '60px', borderTop: '1px solid var(--border-light)', paddingTop: '32px' }}>
        <button className="btn-outline" onClick={onBack}>
          <ArrowLeft size={16} style={{ marginRight: '8px' }} /> Back to Home
        </button>
      </div>
    </div>
  );
};

export default CognitiveTasksScreen;
