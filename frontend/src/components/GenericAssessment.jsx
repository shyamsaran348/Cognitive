import React, { useState, useEffect, useRef } from 'react';
import { Mic, Square, Brain, RefreshCw, AlertCircle, CheckCircle2, ChevronRight, Send, Type, MousePointer2, Loader2, Volume2, PlayCircle } from 'lucide-react';
import TrailMakingTask from './TrailMakingTask';

/**
 * GenericAssessment — High-performance asynchronous assessment runner.
 * Features: Background processing queue, interleaved inputs, and robust Web Speech TTS.
 */
const GenericAssessment = ({ testType, title, onComplete, onBack }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [promptData, setPromptData] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [results, setResults] = useState({});
  const [timer, setTimer] = useState(0);
  const [textInput, setTextInput] = useState('');
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [hasPlayedAudio, setHasPlayedAudio] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const pendingRequestsRef = useRef(0);
  const scoringQueueRef = useRef([]); // NEW: Queue for background scoring
  const finalResultsRef = useRef({});
  const isProcessingQueueRef = useRef(false); // NEW: Track processing state

  useEffect(() => { fetchPrompt(0); }, []);

  // Auto-play TTS when promptData changes
  useEffect(() => {
    if (promptData && promptData.should_speak) {
      setHasPlayedAudio(false);
      const t = setTimeout(() => {
        speak(promptData.prompt);
      }, 500);
      return () => clearTimeout(t);
    }
  }, [promptData]);

  useEffect(() => {
    let interval;
    if (isRecording) interval = setInterval(() => setTimer(p => p + 1), 1000);
    else setTimer(0);
    return () => clearInterval(interval);
  }, [isRecording]);

  const speak = (text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.85;
    utterance.onstart = () => { setIsSpeaking(true); setHasPlayedAudio(true); };
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const fetchPrompt = async (index) => {
    try {
      const res = await fetch(`http://localhost:8000/active_test/prompt?index=${index}&test_type=${testType}`);
      const data = await res.json();
      
      if (data.status === 'success') {
        setPromptData(data.data);
        setTextInput('');
      } else {
        console.log(`[FLOW] End of battery reached for index ${index}`);
        handleBatteryFinish();
      }
    } catch (err) {
      console.error('[FLOW] Failed to fetch prompt:', err);
    }
  };

  const handleBatteryFinish = () => {
    if (pendingRequestsRef.current > 0) {
      setIsFinalizing(true);
      const interval = setInterval(() => {
        if (pendingRequestsRef.current === 0) {
          clearInterval(interval);
          onComplete(finalResultsRef.current);
        }
      }, 500);
    } else {
      onComplete(finalResultsRef.current);
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
    sendToScoreAsync({ audio: audioBlob });
  };

  const handleTextSubmit = (e) => {
    e.preventDefault();
    if (textInput.trim()) {
      sendToScoreAsync({ text: textInput });
    }
  };

  /**
   * Process the background scoring queue one-by-one to avoid browser connection starvation
   */
  const processScoringQueue = async () => {
    if (isProcessingQueueRef.current || scoringQueueRef.current.length === 0) return;
    
    isProcessingQueueRef.current = true;
    while (scoringQueueRef.current.length > 0) {
      const { formData, taskKey } = scoringQueueRef.current.shift();
      
      try {
        const res = await fetch('http://localhost:8000/active_test/score', { method: 'POST', body: formData });
        const data = await res.json();
        const domainResult = { score: data.score, ...(data.metadata || {}) };
        finalResultsRef.current = { ...finalResultsRef.current, [taskKey]: domainResult };
      } catch (err) {
        console.error(`[QUEUE] Background scoring failed for ${taskKey}:`, err);
      } finally {
        pendingRequestsRef.current -= 1;
      }
      
      // Small pause between heavy requests to let UI/network breathe
      await new Promise(r => setTimeout(r, 100));
    }
    isProcessingQueueRef.current = false;
  };

  const sendToScoreAsync = (payload) => {
    pendingRequestsRef.current += 1;
    const taskKey = promptData.key;

    const formData = new FormData();
    if (payload.audio) formData.append('audio', payload.audio, 'response.wav');
    if (payload.text) formData.append('text_response', payload.text);
    formData.append('task_key', taskKey);
    formData.append('test_type', testType);

    // Push to background queue and trigger processing
    scoringQueueRef.current.push({ formData, taskKey });
    processScoringQueue();

    const nextIdx = currentStep + 1;
    setCurrentStep(nextIdx);
    fetchPrompt(nextIdx);
  };

  if (isFinalizing) return (
    <div className="panel-white animate-fade-in" style={{ textAlign: 'center', padding: '100px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <Brain size={64} color="var(--primary)" className="animate-pulse" style={{ marginBottom: '24px' }} />
      <h2 style={{ marginBottom: '12px' }}>Finalizing Clinical Data</h2>
      <p style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Loader2 size={16} className="animate-spin" /> 
        Synthesizing multi-modal biomarkers in the background...
      </p>
    </div>
  );

  if (!promptData) return (
    <div className="panel-white" style={{ textAlign: 'center', padding: '80px' }}>
      <RefreshCw size={32} className="animate-spin" color="var(--primary)" />
      <p style={{ marginTop: '16px', color: 'var(--text-muted)' }}>Loading assessment...</p>
    </div>
  );

  const progress = promptData.total > 0 ? (currentStep / promptData.total) * 100 : 0;
  const isTextMode = promptData.input_mode === 'text';
  const isVisualMode = promptData.input_mode === 'visual';
  const shouldHideText = promptData.hide_text && !results[promptData.key];

  return (
    <div className="active-assessment-screen animate-slide-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <div className="badge-green" style={{ marginBottom: '8px' }}>
            {title} — Task {currentStep + 1} of {promptData.total}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            {isTextMode ? <Type size={12} /> : isVisualMode ? <MousePointer2 size={12} /> : <Mic size={12} />}
            Domain: <strong>{(promptData.domain_label || promptData.key).replace(/_/g, ' ')}</strong>
          </div>
        </div>
        <button className="btn-outline" style={{ fontSize: '0.75rem', padding: '8px 16px' }} onClick={onBack}>Exit</button>
      </div>

      <div style={{ height: '4px', background: 'var(--border-light)', borderRadius: '2px', marginBottom: '32px', overflow: 'hidden' }}>
        <div style={{ width: `${progress}%`, height: '100%', background: 'var(--primary)', borderRadius: '2px', transition: 'width 0.4s ease' }} />
      </div>

      <div className="panel-white" style={{ minHeight: '480px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '40px 60px' }}>
        <div style={{ minHeight: '140px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          {shouldHideText ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }} className="animate-pulse">
              <Volume2 size={56} color="var(--primary)" />
              <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--primary)', letterSpacing: '-0.01em' }}>
                {isSpeaking ? 'Playing Audio Prompt...' : 'Listen carefully to the prompt.'}
              </h2>
              {!isSpeaking && !hasPlayedAudio && (
                <button onClick={() => speak(promptData.prompt)} className="btn-primary" style={{ marginTop: '12px', padding: '12px 24px', borderRadius: '30px' }}>
                   Start Audio <PlayCircle size={20} style={{ marginLeft: '8px' }} />
                </button>
              )}
            </div>
          ) : (
            <h2 style={{ fontSize: isVisualMode ? '1.2rem' : '1.7rem', maxWidth: '750px', lineHeight: '1.5', fontWeight: 600 }}>
              "{promptData.prompt}"
            </h2>
          )}
          
          {promptData.should_speak && !isSpeaking && hasPlayedAudio && (
             <button 
               onClick={() => speak(promptData.prompt)} 
               style={{ 
                 marginTop: '20px', color: 'var(--primary)', border: 'none', 
                 background: 'var(--primary-light)', padding: '8px 16px', borderRadius: '20px',
                 fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                 fontWeight: 600
               }}
             >
               <Volume2 size={16} /> Replay Prompt
             </button>
          )}
        </div>

        <div style={{ width: '100%', maxWidth: isVisualMode ? '700px' : '500px', marginTop: '48px' }}>
          {isVisualMode ? (
            <TrailMakingTask onComplete={(res) => sendToScoreAsync({ text: res })} />
          ) : isTextMode ? (
            <form onSubmit={handleTextSubmit} style={{ width: '100%' }}>
              <input
                type="text"
                autoFocus
                className="input-field"
                placeholder="Type the answer here..."
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                style={{ width: '100%', padding: '20px', borderRadius: '16px', fontSize: '1.2rem', marginBottom: '24px', textAlign: 'center', border: '2px solid var(--primary-light)' }}
              />
              <button type="submit" className="btn-primary" style={{ width: '100%', padding: '16px', gap: '12px' }}>Next Task <ChevronRight size={20} /></button>
            </form>
          ) : (
            <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <button
                disabled={isSpeaking || (promptData.hide_text && !hasPlayedAudio)}
                onClick={isRecording ? stopRecording : startRecording}
                style={{
                  width: '100px', height: '100px', borderRadius: '50%',
                  background: isRecording ? 'var(--danger)' : (isSpeaking || (promptData.hide_text && !hasPlayedAudio)) ? '#e2e8f0' : 'var(--primary)',
                  color: 'white', border: 'none', cursor: (isSpeaking || (promptData.hide_text && !hasPlayedAudio)) ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  boxShadow: isRecording ? '0 0 0 12px rgba(239,68,68,0.15)' : '0 0 0 12px rgba(99,102,241,0.12)',
                  transition: 'all 0.3s',
                  opacity: (isSpeaking || (promptData.hide_text && !hasPlayedAudio)) ? 0.6 : 1
                }}
              >
                {isRecording ? <Square size={32} fill="white" /> : <Mic size={40} />}
              </button>
              {isRecording && (
                <div style={{ position: 'absolute', bottom: '-48px', fontWeight: 800, color: 'var(--danger)', fontSize: '1.1rem' }}>
                  {Math.floor(timer / 60)}:{(timer % 60).toString().padStart(2, '0')}
                </div>
              )}
            </div>
          )}
        </div>

        <div style={{ marginTop: '80px', color: 'var(--text-muted)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '10px', background: '#f8fafc', padding: '12px 20px', borderRadius: '30px' }}>
          <AlertCircle size={16} color="var(--primary)" />
          {isVisualMode 
            ? 'Interactive visual task. Connect the sequence using the buttons.'
            : isTextMode 
                ? 'Type directly in the field. Press Enter to proceed.' 
                : isSpeaking 
                    ? 'Wait for the audio prompt to finish...'
                    : 'Speak clearly. Press the button again to stop recording.'
          }
        </div>
      </div>
    </div>
  );
};

export default GenericAssessment;
