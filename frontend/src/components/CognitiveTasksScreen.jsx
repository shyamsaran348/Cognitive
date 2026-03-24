import React from 'react';
import { Brain, FileText, Layout, ArrowRight, ArrowLeft, Mic, ChevronRight } from 'lucide-react';

const CognitiveTasksScreen = ({ onNext, onBack }) => {
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
      title: 'ACE-III',
      subtitle: 'Addenbrooke’s Cognitive Examination III',
      desc: 'Digitised ACE-III covering attention, memory, verbal fluency, language, and visuospatial abilities.',
      status: 'Coming Soon',
      active: false,
      tags: ['Attention', 'Memory', 'Fluency']
    },
    {
      id: 'moca',
      title: 'MoCA',
      subtitle: 'Montreal Cognitive Assessment',
      desc: 'Digital MoCA screening — especially sensitive for early-stage MCI. Supports Indian language variants.',
      status: 'Coming Soon',
      active: false,
      tags: ['Orientation', 'Recall', 'Attention']
    }
  ];

  return (
    <div className="tasks-page animate-slide-up">
      <div style={{ marginBottom: '48px' }}>
        <div className="badge-green" style={{ marginBottom: '16px' }}>Assessment Suite</div>
        <h2 style={{ fontSize: '3rem', margin: '0 0 20px' }}>Cognitive Test Hub</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem', maxWidth: '800px' }}>
          CogniSense will expand to include digitised versions of standardised cognitive tests. Each test result feeds into the final diagnostic fusion alongside the voice analysis.
        </p>
      </div>

      <div className="test-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
        {tests.map(test => (
          <div 
            key={test.id} 
            className={`panel-white test-card ${test.active ? 'active' : 'disabled'}`}
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              gap: '16px', 
              cursor: test.active ? 'pointer' : 'default',
              opacity: test.active ? 1 : 0.6
            }}
            onClick={test.active ? onNext : null}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
               <div className="stream-icon" style={{ background: test.active ? 'var(--accent)' : 'var(--bg-secondary)' }}>
                 {test.id === 'voice' ? <Mic size={20} /> : test.id === 'ace3' ? <FileText size={20} /> : <Layout size={20} />}
               </div>
               <div className={`badge ${test.active ? 'badge-live' : 'badge-soon'}`} style={{ 
                 fontSize: '0.6rem', padding: '4px 8px', borderRadius: '4px', fontWeight: 800,
                 background: test.active ? '#dcfce7' : '#f1f5f9',
                 color: test.active ? '#166534' : '#64748b'
               }}>
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

            {test.active && (
              <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)', fontWeight: 700, fontSize: '0.9rem' }}>
                Open Assessment <ChevronRight size={16} />
              </div>
            )}
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
