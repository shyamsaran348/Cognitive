import React from 'react';
import { ArrowRight, ArrowLeft, CheckCircle2 } from 'lucide-react';

const PatientProfileScreen = ({ age, setAge, education, setEducation, cdr, setCdr, onNext, onBack }) => {
  const cdrOptions = [
    { value: 0, label: '0', sub: 'Normal' },
    { value: 0.5, label: '0.5', sub: 'Very Mild' },
    { value: 1, label: '1', sub: 'Mild' },
    { value: 2, label: '2', sub: 'Moderate' },
    { value: 3, label: '3', sub: 'Severe' },
  ];

  return (
    <div className="profile-page animate-slide-up">
      <div className="profile-grid">
        {/* Left Column: Context */}
        <div style={{ paddingRight: '40px' }}>
          <h2 style={{ fontSize: '2.5rem', marginBottom: '24px' }}>Patient Profile</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '32px' }}>
            These details help the model calibrate its sensitivity. Cognitive "normal" varies significantly by age and education.
          </p>
          <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {[
              "Age adjusts for natural speech changes in elderly patients",
              "Education reflects cognitive reserve — masking decline longer",
              "CDR provides the neurologist-assessed baseline stage",
              "All fields are processed locally; no data is stored"
            ].map((item, i) => (
              <li key={i} style={{ display: 'flex', gap: '12px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                <CheckCircle2 size={18} color="var(--success)" strokeWidth={3} />
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* Right Column: Form */}
        <div className="panel-white">
          <h3 style={{ marginBottom: '8px' }}>Patient Details</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '32px' }}>
            Please fill in the patient's demographic and clinical information.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '32px' }}>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Patient Age</label>
              <input 
                type="number" 
                className="form-input" 
                value={age} 
                onChange={e => setAge(parseFloat(e.target.value))} 
                placeholder="e.g. 72" 
              />
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '8px', display: 'block' }}>Age in years at time of assessment</span>
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Years of Education</label>
              <input 
                type="number" 
                className="form-input" 
                value={education} 
                onChange={e => setEducation(parseFloat(e.target.value))} 
                placeholder="e.g. 16"
              />
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '8px', display: 'block' }}>Total years of formal schooling</span>
            </div>
          </div>

          <div style={{ marginBottom: '32px' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>CDR — Clinical Dementia Rating</label>
            <div className="cdr-grid">
              {cdrOptions.map(opt => (
                <div 
                  key={opt.value} 
                  className={`cdr-card ${cdr === opt.value ? 'selected' : ''}`}
                  onClick={() => setCdr(opt.value)}
                >
                  <h6 style={{ margin: 0, fontSize: '1.2rem', color: cdr === opt.value ? 'var(--primary)' : 'var(--text-main)' }}>{opt.label}</h6>
                  <p style={{ margin: '4px 0 0', fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{opt.sub}</p>
                </div>
              ))}
            </div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '12px', display: 'block' }}>
              CDR is typically assigned by a neurologist prior to this assessment.
            </span>
          </div>

          <div style={{ display: 'flex', gap: '16px', marginTop: '40px' }}>
            <button className="btn-primary" style={{ flex: 1 }} onClick={onNext}>
              Continue to Audio Upload <ArrowRight size={18} />
            </button>
            <button className="btn-outline" onClick={onBack}>Back</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PatientProfileScreen;
