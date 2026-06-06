import { useState, useEffect, useRef } from 'react';

const initialLogs = [
  "[10:42:01] INFO Worker-3: Fetching RSS feed https://tech.blog/feed",
  "[10:42:02] INFO Worker-3: Parsed 15 new items",
  "[10:42:02] WARN NLP: Entity extraction confidence low for 'QuantumX'",
  "[10:42:03] INFO VectorDB: pgvector check complete. 1 duplicate found.",
  "[10:42:03] INFO LLM: Routing to Groq endpoint...",
  "[10:42:04] SUCCESS: Analyzed signal ID-8829. Relevance: 0.92",
  "[10:42:05] INFO Worker-1: Playwright rendering https://corp.ai/releases",
  "...waiting for new signals..."
];

const newLogs = [
  "[10:45:12] INFO Worker-2: Initializing HTTPX client pool...",
  "[10:45:14] INFO NLP: Loaded en_core_web_trf model in 2.1s",
  "[10:45:15] INFO VectorDB: Connected to pgvector instance.",
  "[10:45:18] SUCCESS: Processed batch 409A. 24 entities extracted.",
  "[10:45:22] INFO LLM: Gemini inference latency: 850ms",
  "[10:45:25] WARN Worker-1: Rate limit approaching for source X.",
  "[10:45:30] INFO Pipeline: 120 signals processed this minute."
];

export default function TerminalLog() {
  const [logs, setLogs] = useState(initialLogs.join('\n'));
  const logRef = useRef(null);

  useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      setLogs(prev => {
        if (index < newLogs.length) {
          const nextLine = newLogs[index];
          index++;
          return prev + '\n' + nextLine;
        } else {
          index = 0;
          return prev; // Or reset if we want it to loop indefinitely adding more
        }
      });
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="bg-surface-elevated border border-border-subtle rounded p-stack-md h-[400px] flex flex-col glow-edge">
      <div className="flex items-center justify-between border-b border-border-subtle pb-stack-sm mb-stack-sm">
        <h3 className="font-label-md text-label-md text-primary font-bold">Terminal</h3>
        <span className="font-label-sm text-label-sm text-on-surface-variant text-[11px]">tail -f ingestion.log</span>
      </div>
      <div 
        ref={logRef}
        className="flex-grow overflow-y-auto bg-[#050505] p-stack-sm rounded border border-border-subtle font-label-sm text-label-sm text-[11px] terminal-log whitespace-pre-wrap"
      >
        {logs}
      </div>
    </div>
  );
}
