import React, { useState, useEffect, useRef } from 'react';
import { Mic, Square, Brain, RefreshCw, AlertCircle, CheckCircle2, ChevronRight } from 'lucide-react';

/**
 * GenericAssessment — Reusable voice-driven assessment runner.
 * Accepts a `testType` ("ace3" | "moca") and runs the matching battery from the backend.
 */
const GenericAssessment = ({ testType, title, onComplete, onBack }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [promptData, setPromptData] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState({});
  const [timer, setTimer] = useState(0);
  const [lastScore, setLastScore] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => { fetchPrompt(0); }, []);

  useEffect(() => {
    let interval;
    if (isRecording) interval = setInterval(() => setTimer(p => p + 1), 1000);
    else setTimer(0);
    return () => clearInterval(interval);
  }, [isRecording]);

  const fetchPrompt = async (index) => {
    try {
      const res = await fetch(`http://localhost:8000/active_test/prompt?index=${index}&test_type=${testType}`);
      const data = await res.json();
      if (data.status === 'success') {
        setPromptData(data.data);
        setLastScore(null);
      } else {
        onComplete(results);
      }
    } catch (err) {
      console.error('Failed to fetch prompt:', err);
    }
  };

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorderRef.current = new MediaRecorder(stream);
    audioChunksRef.current = [];
    mediaRecorderRef.current.ondataavailable = (e) => audioChunksRef.current.push(e.data);
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
    formData.append('test_type', testType);

    try {
      const res = await fetch('http://localhost:8000/active_test/score', { method: 'POST', body: formData });
      const data = await res.json();
      const domainResult = { score: data.score, ...(data.metadata || {}) };
      setResults(prev => ({ ...prev, [promptData.key]: domainResult }));
      setLastScore({ score: data.score, max: promptData.points, transcript: data.transcript });
      setIsProcessing(false);

      setTimeout(() => {
        const nextIdx = currentStep + 1;
        setCurrentStep(nextIdx);
        fetchPrompt(nextIdx);
      }, 1800);
    } catch (err) {
      console.error('Scoring failed:', err);
      setIsProcessing(false);
    }
  };

  if (!promptData) return (
    <div className="panel-white" style={{ textAlign: 'center', padding: '80px' }}>
      <RefreshCw size={32} className="animate-spin" color="var(--primary)" />
      <p style={{ marginTop: '16px', color: 'var(--text-muted)' }}>Loading assessment...</p>
    </div>
  );

  const progress = promptData.total > 0 ? (currentStep / promptData.total) * 100 : 0;

  return (
    <div className="active-assessment-screen animate-slide-up">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <div className="badge-green" style={{ marginBottom: '8px' }}>
            {title} — Task {currentStep + 1} of {promptData.total}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Domain: <strong>{(promptData.domain_label || promptData.key).replace(/_/g, ' ')}</strong>
          </div>
        </div>
        <button className="btn-outline" style={{ fontSize: '0.75rem', padding: '8px 16px' }} onClick={onBack}>
          Exit Assessment
        </button>
      </div>

      {/* Progress Bar */}
      <div style={{ height: '4px', background: 'var(--border-light)', borderRadius: '2px', marginBottom: '32px', overflow: 'hidden' }}>
        <div style={{ width: `${progress}%`, height: '100%', background: 'var(--primary)', borderRadius: '2px', transition: 'width 0.4s ease' }} />
      </div>

      {/* Task Panel */}
      <div className="panel-white" style={{ minHeight: '420px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '60px 80px' }}>
        
        {/* Prompt text */}
        <h2 style={{ fontSize: '1.7rem', maxWidth: '700px', marginBottom: '48px', lineHeight: '1.5', fontWeight: 600 }}>
          "{promptData.prompt}"
        </h2>

        {/* Feedback from last answer */}
        {lastScore && !isProcessing && (
          <div style={{ marginBottom: '24px', padding: '12px 24px', background: lastScore.score > 0 ? '#d1fae5' : '#fef2f2', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            {lastScore.score > 0 ? <CheckCircle2 size={16} color="#065f46" /> : <AlertCircle size={16} color="#991b1b" />}
            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: lastScore.score > 0 ? '#065f46' : '#991b1b' }}>
              Scored {lastScore.score}/{lastScore.max}
              {lastScore.transcript ? ` · Heard: "${lastScore.transcript.slice(0, 60)}${lastScore.transcript.length > 60 ? '…' : ''}"` : ''}
            </span>
          </div>
        )}

        {/* Record button */}
        {isProcessing ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
            <RefreshCw size={48} className="animate-spin" color="var(--primary)" />
            <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>Analyzing with Whisper ASR…</span>
          </div>
        ) : (
          <div style={{ position: 'relative' }}>
            <button
              onClick={isRecording ? stopRecording : startRecording}
              style={{
                width: '96px', height: '96px', borderRadius: '50%',
                background: isRecording ? 'var(--danger)' : 'var(--primary)',
                color: 'white', border: 'none', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: isRecording ? '0 0 0 12px rgba(239,68,68,0.15)' : '0 0 0 12px rgba(99,102,241,0.12)',
                transition: 'all 0.3s'
              }}
            >
              {isRecording ? <Square size={32} fill="white" /> : <Mic size={40} />}
            </button>
            {isRecording && (
              <div style={{ position: 'absolute', bottom: '-36px', left: '50%', transform: 'translateX(-50%)', fontWeight: 800, color: 'var(--danger)' }}>
                {Math.floor(timer / 60)}:{(timer % 60).toString().padStart(2, '0')}
              </div>
            )}
          </div>
        )}

        <div style={{ marginTop: '60px', color: 'var(--text-muted)', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={14} />
          Speak clearly. Press the button again to stop recording.
        </div>
      </div>
    </div>
  );
};

export default GenericAssessment;
