import React, { useState, useEffect, useRef } from 'react';
import { CheckCircle2, AlertCircle, RotateCcw } from 'lucide-react';

/**
 * TrailMakingTask — Interactive Executive Function Probe.
 * Target Sequence: 1 -> A -> 2 -> B -> 3 -> C -> 4 -> D -> 5 -> E
 */
const TrailMakingTask = ({ onComplete }) => {
  const sequence = ['1', 'A', '2', 'B', '3', 'C', '4', 'D', '5', 'E'];
  
  // Fixed Clinical Layout (Simulating the ACE-III / MoCA paper test)
  const nodes = [
    { id: '1', x: 20, y: 20 },
    { id: 'A', x: 70, y: 15 },
    { id: '2', x: 45, y: 40 },
    { id: 'B', x: 15, y: 65 },
    { id: '3', x: 80, y: 75 },
    { id: 'C', x: 50, y: 90 },
    { id: '4', x: 10, y: 35 },
    { id: 'D', x: 85, y: 45 },
    { id: '5', x: 30, y: 75 },
    { id: 'E', x: 65, y: 60 },
  ];

  const [clicked, setClicked] = useState([]);
  const [error, setError] = useState(null);
  const [isFinished, setIsFinished] = useState(false);

  const handleNodeClick = (nodeId) => {
    if (isFinished) return;
    
    const currentIndex = clicked.length;
    const expectedNode = sequence[currentIndex];

    if (nodeId === expectedNode) {
      const newClicked = [...clicked, nodeId];
      setClicked(newClicked);
      setError(null);

      if (newClicked.length === sequence.length) {
        setIsFinished(true);
        setTimeout(() => onComplete("success"), 1500);
      }
    } else {
      setError(`Incorrect sequence. Expected ${expectedNode}.`);
      setTimeout(() => setError(null), 1500);
    }
  };

  const reset = () => {
    setClicked([]);
    setError(null);
    setIsFinished(false);
  };

  return (
    <div className="trail-making-container" style={{ width: '100%', maxWidth: '600px', margin: '0 auto' }}>
      <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          Click the nodes in order: <strong>1 → A → 2 → B...</strong>
        </p>
        <button className="btn-outline" onClick={reset} style={{ padding: '6px 12px', fontSize: '0.75rem', gap: '6px' }}>
           <RotateCcw size={14} /> Reset
        </button>
      </div>

      <div className="trail-canvas-wrapper" style={{ 
        position: 'relative', width: '100%', paddingBottom: '75%', 
        background: '#f8fafc', borderRadius: '24px', border: '2px dashed var(--border-light)',
        overflow: 'hidden'
      }}>
        {/* SVG for Lines */}
        <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
           {clicked.map((id, index) => {
             if (index === 0) return null;
             const fromNode = nodes.find(n => n.id === clicked[index - 1]);
             const toNode = nodes.find(n => n.id === id);
             return (
               <line 
                 key={index}
                 x1={`${fromNode.x}%`} y1={`${fromNode.y}%`}
                 x2={`${toNode.x}%`} y2={`${toNode.y}%`}
                 stroke="var(--primary)" strokeWidth="3" strokeLinecap="round"
                 className="animate-draw-line"
               />
             );
           })}
        </svg>

        {/* Nodes */}
        {nodes.map(node => {
          const isClicked = clicked.includes(node.id);
          const isNext = !isFinished && sequence[clicked.length] === node.id;
          
          return (
            <button
              key={node.id}
              onClick={() => handleNodeClick(node.id)}
              className={`trail-node ${isClicked ? 'active' : ''} ${isNext ? 'pulse' : ''}`}
              style={{
                position: 'absolute',
                top: `${node.y}%`, left: `${node.x}%`,
                width: '48px', height: '48px', borderRadius: '50%',
                transform: 'translate(-50%, -50%)',
                background: isClicked ? 'var(--primary)' : 'white',
                color: isClicked ? 'white' : 'var(--text-main)',
                border: isClicked ? 'none' : '2px solid var(--border-light)',
                fontWeight: 700, fontSize: '1.2rem', cursor: 'pointer',
                transition: 'all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
                boxShadow: isClicked ? '0 8px 16px rgba(99,102,241,0.25)' : '0 4px 6px rgba(0,0,0,0.05)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                zIndex: 2
              }}
            >
              {node.id}
            </button>
          );
        })}

        {/* Success Overlay */}
        {isFinished && (
           <div className="animate-fade-in" style={{ 
             position: 'absolute', inset: 0, background: 'rgba(255,255,255,0.8)', 
             display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
             zIndex: 10, backdropFilter: 'blur(4px)'
           }}>
             <div style={{ background: 'white', padding: '32px', borderRadius: '24px', boxShadow: '0 20px 40px rgba(0,0,0,0.1)', textAlign: 'center' }}>
               <CheckCircle2 size={48} color="#10b981" style={{ marginBottom: '16px' }} />
               <h3 style={{ margin: 0, color: 'var(--text-main)' }}>Sequence Correct</h3>
               <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '8px' }}>Proceeding to next task...</p>
             </div>
           </div>
        )}

        {/* Error Tooltip */}
        {error && (
          <div style={{ 
            position: 'absolute', bottom: '20px', left: '50%', transform: 'translateX(-50%)',
            background: 'var(--danger)', color: 'white', padding: '8px 16px', borderRadius: '12px',
            fontSize: '0.8rem', fontWeight: 600, boxShadow: '0 4px 12px rgba(239,68,68,0.2)'
          }}>
            <AlertCircle size={14} inline /> {error}
          </div>
        )}
      </div>

      <style>{`
        .trail-node.pulse {
          box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4);
          animation: node-pulse 2s infinite;
        }
        @keyframes node-pulse {
          0% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }
          70% { box-shadow: 0 0 0 10px rgba(99, 102, 241, 0); }
          100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
        }
        .animate-draw-line {
          stroke-dasharray: 1000;
          stroke-dashoffset: 1000;
          animation: draw-line 0.5s ease-out forwards;
        }
        @keyframes draw-line {
          to { stroke-dashoffset: 0; }
        }
      `}</style>
    </div>
  );
};

export default TrailMakingTask;
