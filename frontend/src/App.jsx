import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  CheckCircle2, Loader2, ArrowRight, ArrowLeft, 
  Home, Activity, Layout, Shield, Brain, User, 
  Database, LineChart, ChevronRight, Play, Upload, Mic
} from 'lucide-react';
import './App.css';

// Modular Components
import WelcomeScreen from './components/WelcomeScreen';
import PatientProfileScreen from './components/PatientProfileScreen';
import CognitiveTasksScreen from './components/CognitiveTasksScreen';
import IngestionPanel from './components/IngestionPanel';
import DiagnosticResult from './components/DiagnosticResult';
import SessionHistory from './components/SessionHistory';
import TrainingMetrics from './components/TrainingMetrics';
import TemporalTrend from './components/TemporalTrend';
import ClinicalSummary from './components/ClinicalSummary';
import ActiveAssessment from './components/ActiveAssessment';
import GenericAssessment from './components/GenericAssessment';

const FlowStepper = ({ currentStep }) => {
  const steps = ["Orientation", "Clinical Details", "Audio Data", "Analysis"];
  return (
    <div className="flow-stepper">
      {steps.map((s, i) => (
        <React.Fragment key={i}>
          <div className={`flow-step ${i + 1 <= currentStep ? 'done' : i + 1 === currentStep + 1 ? 'active' : ''}`}>
            <div className="step-dot">{i + 1 < currentStep ? <CheckCircle2 size={12} /> : i + 1}</div>
            <span>{s}</span>
          </div>
          {i < steps.length - 1 && <div style={{ width: '40px', height: '1.5px', background: 'var(--border-light)' }} />}
        </React.Fragment>
      ))}
    </div>
  );
};

function App() {
  const [currentStep, setCurrentStep] = useState(0); // 0:Home 1:Profile 2:Tasks 3:Audio 4:Result 5:ActiveAssess 6:ACE3 7:MoCA
  const [selectedTest, setSelectedTest] = useState('voice'); // which test was chosen in the hub
  const [file, setFile] = useState(null);
  const [age, setAge] = useState(65.0);
  const [education, setEducation] = useState(12.0);
  const [cdr, setCdr] = useState(0.5);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null); 
  const [activeResults, setActiveResults] = useState(null); 
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [liveWaveform, setLiveWaveform] = useState(Array(40).fill(0));
  const [steps, setSteps] = useState([]); 
  const audioContextRef = React.useRef(null);
  const analyserRef = React.useRef(null);
  const animationRef = React.useRef(null);

  useEffect(() => {
    fetchHistory();
  }, [results]); 

  const fetchHistory = async () => {
    try {
      const resp = await axios.get("http://localhost:8000/history");
      if (resp.data.status === "success") {
        setHistory(resp.data.history.reverse());
      }
    } catch (err) {
      console.warn("History fetch failed");
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      analyserRef.current = audioContextRef.current.createAnalyser();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      analyserRef.current.fftSize = 64;
      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const updateWave = () => {
        analyserRef.current.getByteFrequencyData(dataArray);
        setLiveWaveform(Array.from(dataArray).map(v => v / 255));
        animationRef.current = requestAnimationFrame(updateWave);
      };
      updateWave();

      const recorder = new MediaRecorder(stream);
      const chunks = [];
      recorder.ondataavailable = e => chunks.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/wav' });
        setFile(new File([blob], "live_record.wav", { type: 'audio/wav' }));
        if (animationRef.current) cancelAnimationFrame(animationRef.current);
        if (audioContextRef.current) audioContextRef.current.close();
      };
      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      setError("");
    } catch (err) {
      setError("Microphone access denied.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files[0]) {
      setFile(e.target.files[0]);
      setResults(null); 
    }
  };

  const handleAnalyze = async () => {
    if (!file) return setError("Audio input required.");
    setIsLoading(true); 
    setResults(null); 
    setError("");
    setSteps([
      { id: 1, label: "Neural ASR Layer", status: 'active' },
      { id: 2, label: "Biomarker Extraction", status: 'pending' },
      { id: 3, label: "Bayesian PoE Fusion", status: 'pending' }
    ]);

    const formData = new FormData();
    formData.append("audio", file);
    formData.append("age", age);
    formData.append("education", education);
    formData.append("cdr", cdr);

    try {
      setTimeout(() => setSteps(s => s.map(x => x.id === 1 ? { ...x, status: 'done' } : x.id === 2 ? { ...x, status: 'active' } : x)), 1200);
      setTimeout(() => setSteps(s => s.map(x => x.id === 2 ? { ...x, status: 'done' } : x.id === 3 ? { ...x, status: 'active' } : x)), 2400);

      const res = await axios.post("http://localhost:8000/predict", formData);
      if (res.data.status === "success") {
        const data = res.data.data; 
        setResults(data); 
        setSteps(s => s.map(x => ({ ...x, status: 'done' })));

        if (data.trigger_active_test) {
          setCurrentStep(5); 
        } else {
          setCurrentStep(4); 
        }
        fetchHistory(); 
      } else {
        setError(res.data.message);
      }
    } catch (err) {
      setError("Inference server offline.");
    }
    setIsLoading(false); 
  };

  const handleBack = () => setCurrentStep(prev => Math.max(0, prev - 1));
  const handleNext = () => setCurrentStep(prev => Math.min(5, prev + 1)); 

  return (
    <div className="clinical-app">
      <nav className="navbar">
        <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Brain size={28} color="var(--primary)" />
          <span style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--primary)', letterSpacing: '-0.03em' }}>Cogni<span style={{ color: 'var(--primary-light)' }}>Sense</span></span>
        </div>
        <div className="nav-links">
          <a className={currentStep === 0 ? 'active' : ''} onClick={() => setCurrentStep(0)}>Home</a>
          <a className={currentStep > 0 && currentStep < 4 ? 'active' : ''} onClick={() => setCurrentStep(1)}>Assessment</a>
          <a onClick={() => setCurrentStep(2)}>Test Hub</a>
        </div>
        <div className="nav-actions">
          <button className="btn-primary" onClick={() => setCurrentStep(1)}>
            Begin Assessment <ArrowRight size={16} />
          </button>
        </div>
      </nav>

      <main>
        {currentStep === 0 && (
          <div className="container">
            <WelcomeScreen onStart={() => setCurrentStep(1)} />
            <ClinicalSummary history={history} />
          </div>
        )}

        {currentStep > 0 && currentStep < 4 && (
          <div className="container animate-slide-up" style={{ maxWidth: '1000px' }}>
             <FlowStepper currentStep={currentStep} />
             
             {currentStep === 1 && (
               <PatientProfileScreen 
                 age={age} setAge={setAge} 
                 education={education} setEducation={setEducation}
                 cdr={cdr} setCdr={setCdr}
                 onNext={handleNext} onBack={() => setCurrentStep(0)}
               />
             )}

             {currentStep === 2 && (
               <CognitiveTasksScreen
                 onSelectTest={(testId) => {
                   setSelectedTest(testId);
                   if (testId === 'voice') setCurrentStep(3);
                   else if (testId === 'ace3') setCurrentStep(6);
                   else if (testId === 'moca') setCurrentStep(7);
                 }}
                 onBack={handleBack}
               />
             )}

             {currentStep === 3 && (
               <IngestionPanel 
                 file={file} handleFileChange={handleFileChange} 
                 isRecording={isRecording} startRecording={startRecording} stopRecording={stopRecording}
                 liveWaveform={liveWaveform} result={results} 
                 loading={isLoading} steps={steps} 
                 handleAnalyze={handleAnalyze} hideMetadata={true}
                 onBack={handleBack}
               />
             )}
          </div>
        )}

        {currentStep === 4 && (
          <div className="container animate-slide-up" style={{ maxWidth: '1200px' }}>
             <DiagnosticResult result={results} activeResults={activeResults} />
             <div style={{ marginTop: '40px', display: 'flex', justifyContent: 'center' }}>
                <button className="btn-outline" onClick={() => setCurrentStep(0)}>Return to Dashboard</button>
             </div>
          </div>
        )}

        {currentStep === 5 && (
          <div className="container" style={{ maxWidth: '1000px' }}>
             <ActiveAssessment onComplete={async (activeData) => {
               setActiveResults(activeData);
               try {
                 const res = await axios.post("http://localhost:8000/active_test/finalize", {
                   passive_data: results,
                   active_results: activeData
                 });
                 if (res.data.status === 'success') {
                   setResults(res.data.data); // Update with fused data
                 }
               } catch (err) {
                 console.error("Final synthesis failed:", err);
               }
               setCurrentStep(4);
             }} />
          </div>
        )}

        {/* ACE-III Assessment */}
        {currentStep === 6 && (
          <div className="container" style={{ maxWidth: '1000px' }}>
            <GenericAssessment
              testType="ace3"
              title="ACE-III Assessment"
              onBack={() => setCurrentStep(2)}
              onComplete={(data) => {
                setActiveResults(data);
                setCurrentStep(2);
              }}
            />
          </div>
        )}

        {/* MoCA Assessment */}
        {currentStep === 7 && (
          <div className="container" style={{ maxWidth: '1000px' }}>
            <GenericAssessment
              testType="moca"
              title="MoCA Assessment"
              onBack={() => setCurrentStep(2)}
              onComplete={(data) => {
                setActiveResults(data);
                setCurrentStep(2);
              }}
            />
          </div>
        )}
      </main>

      <footer className="webflow-footer" style={{ borderTop: '1px solid var(--border-light)', marginTop: '80px', background: 'var(--white)' }}>
        CogniSense v2.45 Clinical Intelligence • {new Date().getFullYear()} • Restricted to Certified Practitioners
      </footer>
    </div>
  );
}

export default App;
