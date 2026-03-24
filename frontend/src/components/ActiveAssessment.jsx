import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, Square, ChevronRight, Brain, 
  Clock, AlertCircle, CheckCircle2, RefreshCw 
} from 'lucide-react';

const ActiveAssessment = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [promptData, setPromptData] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState({});
  const [timer, setTimer] = useState(0);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    fetchPrompt(0);
  }, []);

  useEffect(() => {
    let interval;
    if (isRecording) {
      interval = setInterval(() => setTimer(prev => prev + 1), 1000);
    } else {
      setTimer(0);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  const fetchPrompt = async (index) => {
    try {
      const res = await fetch(`http://localhost:8000/active_test/prompt?index=${index}`);
      const data = await res.json();
      if (data.status === 'success') {
        setPromptData(data.data);
      } else {
        onComplete(results);
      }
    } catch (err) {
      console.error("Failed to fetch prompt:", err);
    }
  };

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorderRef.current = new MediaRecorder(stream);
    audioChunksRef.current = [];
    
    mediaRecorderRef.current.ondataavailable = (e) => {
      audioChunksRef.current.push(e.data);
    };
    
    mediaRecorderRef.current.onstop = handleStop;
    mediaRecorderRef.current.start();
    setIsRecording(true);
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleStop = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
    sendToScore(audioBlob);
  };

  const sendToScore = async (blob) => {
    setIsProcessing(true);
    const formData = new FormData();
    formData.append('audio', blob, 'response.wav');
    formData.append('task_key', promptData.key);
    
    try {
      const res = await fetch('http://localhost:8000/active_test/score', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      
      setResults(prev => ({ ...prev, [promptData.key]: data }));
      setIsProcessing(false);
      
      // Auto-advance after a brief delay
      setTimeout(() => {
        const nextIdx = currentStep + 1;
        setCurrentStep(nextIdx);
        fetchPrompt(nextIdx);
      }, 1500);
      
    } catch (err) {
      console.error("Scoring failed:", err);
      setIsProcessing(false);
    }
  };

  if (!promptData) return <div className="panel-white">Finalizing Report...</div>;

  return (
    <div className="active-assessment-screen animate-slide-up">
      <div className="badge-green" style={{ marginBottom: '16px' }}>Phase 2: Active Cognitive Probe</div>
      
      <div className="panel-white" style={{ minHeight: '400px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '60px' }}>
         <div style={{ marginBottom: '40px' }}>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginBottom: '24px' }}>
               {[...Array(promptData.total)].map((_, i) => (
                 <div key={i} style={{ width: '40px', height: '4px', background: i <= currentStep ? 'var(--primary)' : 'var(--border-light)', borderRadius: '2px' }} />
               ))}
            </div>
            <h4 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              Domain: {promptData.key.replace('_', ' ')}
            </h4>
         </div>

         <h2 style={{ fontSize: '2rem', maxWidth: '700px', marginBottom: '48px', lineHeight: '1.4' }}>
            "{promptData.prompt}"
         </h2>

         <div style={{ position: 'relative' }}>
            {isProcessing ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
                <RefreshCw size={48} className="animate-spin" color="var(--primary)" />
                <span style={{ fontWeight: 600 }}>Analyzing Response...</span>
              </div>
            ) : (
              <button 
                onClick={isRecording ? stopRecording : startRecording}
                className={`record-btn-large ${isRecording ? 'recording' : ''}`}
                style={{
                  width: '100px', height: '100px', borderRadius: '50%', 
                  background: isRecording ? 'var(--danger)' : 'var(--primary)',
                  color: 'white', border: 'none', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  boxShadow: '0 0 0 10px rgba(0,0,0,0.05)', transition: 'all 0.3s'
                }}
              >
                {isRecording ? <Square size={32} fill="white" /> : <Mic size={40} />}
              </button>
            )}
            
            {isRecording && (
              <div style={{ position: 'absolute', bottom: '-40px', left: '50%', transform: 'translateX(-50%)', fontWeight: 800, color: 'var(--danger)' }}>
                {Math.floor(timer / 60)}:{(timer % 60).toString().padStart(2, '0')}
              </div>
            )}
         </div>

         <div style={{ marginTop: '60px', color: 'var(--text-muted)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} /> 
            Speak clearly into the microphone. Press the button to stop when finished.
         </div>
      </div>
    </div>
  );
};

export default ActiveAssessment;
