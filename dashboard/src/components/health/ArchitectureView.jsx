import { useHealthData } from '../../hooks/useHealthData';
import PipelineStage from './PipelineStage';
import TerminalLog from './TerminalLog';
import TelemetryGrid from './TelemetryGrid';
import ExecutionTable from './ExecutionTable';

export default function ArchitectureView() {
  const { data, loading, error, refetch } = useHealthData(true);

  return (
    <div id="view-health" className="max-w-container-max mx-auto w-full px-margin-mobile md:px-margin-desktop py-stack-lg">
      <header className="mb-stack-lg border-b border-border-subtle pb-stack-md">
        <h1 className="font-display-lg text-display-lg text-primary mb-stack-sm">System Architecture & Operations</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant max-w-3xl">
          A deep dive into the technical intelligence pipeline. Designed for high-throughput, low-latency ingestion and semantic processing.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter items-start">
        {/* Left Column: Ingestion Layers */}
        <div className="lg:col-span-8 flex flex-col gap-stack-lg relative">
          <PipelineStage 
            number="01" 
            title="Ingestion Layer" 
            description="The primary collection gateway utilizing concurrent asynchronous workers. Handles heterogeneous data sources including raw HTTP(S), RSS feeds, and dynamic JS-rendered DOMs."
            status="Active"
            tools={[
              { name: 'HTTPX', subtitle: 'Async Requests' },
              { name: 'Playwright', subtitle: 'Headless Browser' },
              { name: 'RSS/Atom', subtitle: 'Feed Parsers' }
            ]}
          />
          <div className="connector-line h-6"></div>

          <PipelineStage 
            number="02" 
            title="NLP & NER" 
            description="Initial structuring and entity extraction via fine-tuned spaCy pipelines. Focuses on identifying technical terminology, organizations, and specific technology stacks."
            status="Active"
          />
          <div className="connector-line h-6"></div>

          <PipelineStage 
            number="03" 
            title="Deduplication Vector Search" 
            description="Semantic deduplication using pgvector. Computes embeddings for incoming texts and performs cosine similarity checks against recent historical data to prevent duplicate signal processing."
            status="Active"
          />
          <div className="connector-line h-6"></div>

          <PipelineStage 
            number="04" 
            title="LLM Analysis Layer" 
            description="Deep semantic analysis using a combination of fast inference endpoints (Groq) for initial triage and high-parameter models (Gemini) for complex reasoning and summarization."
            status="Active"
          />
        </div>

        {/* Right Column: Telemetry & Terminal */}
        <div className="lg:col-span-4 flex flex-col gap-stack-lg">
          <TerminalLog />
          <TelemetryGrid healthData={data} />
        </div>
      </div>

      {/* Live Execution History Table */}
      <section className="mt-12 bg-surface-elevated border border-border-subtle rounded-lg overflow-hidden shadow-2xl">
        <div className="px-margin-mobile md:px-margin-desktop py-5 border-b border-border-subtle flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h2 className="text-xs font-bold text-white uppercase tracking-wider">Pipeline Execution History</h2>
            <p className="text-[10px] text-on-surface-variant mt-1">Chronological run performance and health records</p>
          </div>
          <button onClick={refetch} className="bg-surface-container hover:bg-surface-container-high text-primary border border-border-subtle text-xs font-semibold px-4 py-2 rounded transition flex-shrink-0">
            Refresh Metrics
          </button>
        </div>
        <div className="overflow-x-auto w-full">
          <ExecutionTable data={data} loading={loading} error={error} />
        </div>
      </section>
    </div>
  );
}
