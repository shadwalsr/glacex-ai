/**
 * GlaceX.ai Curated Offline Intelligence Corpus & Fallback Dataset
 * Used when the remote Supabase data lake is unreachable, paused, or operating offline.
 */

export const MOCK_ARTICLES = [
  {
    id: "art-101",
    title: "DeepSeek-V3: Multi-Head Latent Attention and DualPipe Parallelism Architecture",
    clean_text: "DeepSeek-V3 introduces an innovative mixture-of-experts (MoE) foundation model comprising 671 billion total parameters with 37 billion activated per token. The core architectural leap involves Multi-Head Latent Attention (MLA), which compresses Key-Value (KV) cache into low-dimensional latent vectors, drastically reducing memory footprint during inference while outperforming standard Multi-Head Attention. The training infrastructure utilizes DualPipe, an overlap-centric pipeline parallelism algorithm that overlaps computation with inter-node communication, achieving near-perfect GPU compute utilization on clusters with standard RoCE v2 networks without requiring custom InfiniBand topologies.",
    url: "https://arxiv.org/abs/2412.19437",
    source_name: "arXiv cs.AI",
    published_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    scraped_at: new Date(Date.now() - 3600000 * 1).toISOString(),
    classifications: [
      {
        id: "cls-101",
        category: "paper",
        subcategory: "Transformer Architecture",
        importance: 96,
        is_ai_relevant: true,
        technical_depth: "Deep Mathematical",
        reason: "Breakthrough in KV-cache compression and inter-GPU communication scheduling that drastically cuts training and inference costs for frontier-class open models."
      }
    ],
    insights: [
      {
        id: "ins-101",
        headline: "Multi-Head Latent Attention drops KV cache bandwidth demands by 93% while matching standard attention perplexity.",
        tldr: [
          "Compresses key-value states into low-rank projection latent spaces to minimize memory memory bound during inference decoding.",
          "DualPipe schedules forward and backward chunks across layers to fully mask cross-node all-to-all communication overhead.",
          "FP8 mixed-precision training framework with fine-grained block-level quantization preserves training stability across 14.8T tokens."
        ],
        technical_depth: "Architectural MoE formulation with novel latent caching dynamics.",
        practical_utility: "Allows high-throughput serving of frontier models on commodity dense GPU nodes with reduced high-bandwidth memory pressure.",
        ecosystem_impact: "Accelerated adoption of MLA in subsequent open and proprietary model families, challenging conventional dense architectures.",
        related_papers: ["arXiv:2401.06038", "arXiv:2309.06180"],
        related_entities: ["DeepSeek", "NVIDIA H800", "PyTorch", "FlashAttention"],
        tags: ["MoE", "MLA", "DualPipe", "FP8 Quantization", "Inference Efficiency"]
      }
    ],
    user_feedback: [{ rating: "good" }]
  },
  {
    id: "art-102",
    title: "vLLM 0.7: Asynchronous Engine Core, Chunked Prefill, and Speculative Decoding",
    clean_text: "vLLM version 0.7 rearchitects the serving runtime around an asynchronous Rust/C++ orchestrator that eliminates Python GIL latency in the request loop. The update stabilizes Chunked Prefill, dynamically interleaving compute-bound prompt processing with memory-bound token generation chunks to smooth out GPU compute spikes and prevent latency bubbles. Additionally, multi-candidate speculative decoding support is integrated with hardware-accelerated draft verification kernels, delivering 2.8x-3.4x higher token generation throughput on NVIDIA Hopper and Blackwell architectures.",
    url: "https://blog.vllm.ai/2025/01/vllm-v07-release.html",
    source_name: "Open Source AI Systems",
    published_at: new Date(Date.now() - 3600000 * 5).toISOString(),
    scraped_at: new Date(Date.now() - 3600000 * 3).toISOString(),
    classifications: [
      {
        id: "cls-102",
        category: "tool",
        subcategory: "Serving Infrastructure",
        importance: 92,
        is_ai_relevant: true,
        technical_depth: "Production Systems",
        reason: "Major architectural overhaul resolving long-standing GIL and prefill-headroom bottlenecks in production LLM inference clusters."
      }
    ],
    insights: [
      {
        id: "ins-102",
        headline: "Chunked prefill and native C++ request dispatch unlock 3.2x lower time-to-first-token (TTFT) under sustained concurrency.",
        tldr: [
          "Decouples prompt scheduling from token decoding passes to maintain steady 90%+ tensor core utilization.",
          "Integrates tree-based speculative decoding kernels verifying up to 5 speculative draft tokens in a single forward pass.",
          "Reduces P99 latency spikes during batch ingestion of long context documents."
        ],
        practical_utility: "Direct drop-in replacement for production inference pods requiring strict SLA compliance for streaming responses.",
        ecosystem_impact: "Sets the benchmark for low-latency production inference serving runtimes across the enterprise.",
        related_papers: ["arXiv:2309.06180", "arXiv:2302.01318"],
        related_entities: ["vLLM", "NVIDIA Hopper", "CUDA", "Triton"],
        tags: ["Inference", "Speculative Decoding", "Chunked Prefill", "CUDA", "LLMOps"]
      }
    ],
    user_feedback: []
  },
  {
    id: "art-103",
    title: "Model Context Protocol (MCP): Open Architecture for LLM Tool Integration",
    clean_text: "Anthropic has released the Model Context Protocol (MCP), an open standardized communication protocol enabling AI models to seamlessly connect to external tools, databases, development environments, and internal company repositories. MCP addresses the fragmentation of custom agent connectors by providing a client-host-server specification with bidirectional JSON-RPC transports. Servers expose tools, resources, and prompt templates, with built-in capability negotiation, stateful session handling, and security sandboxing protocols.",
    url: "https://www.anthropic.com/news/model-context-protocol",
    source_name: "Anthropic News",
    published_at: new Date(Date.now() - 3600000 * 12).toISOString(),
    scraped_at: new Date(Date.now() - 3600000 * 8).toISOString(),
    classifications: [
      {
        id: "cls-103",
        category: "tool",
        subcategory: "Agent Protocols",
        importance: 95,
        is_ai_relevant: true,
        technical_depth: "Architectural Spec",
        reason: "Industry-standard open protocol establishing interoperability between frontier LLM agents and enterprise data assets."
      }
    ],
    insights: [
      {
        id: "ins-103",
        headline: "Standardized JSON-RPC protocol replaces ad-hoc API integrations with unified agent resource discovery.",
        tldr: [
          "Formalizes three distinct primitive constructs: Prompts (user intent), Resources (context data), and Tools (executable actions).",
          "Supports stdio, SSE, and WebSocket transports with streaming payload support.",
          "Rapid ecosystem adoption across major developer tools including Claude Desktop, Antigravity IDE, Cursor, and Zed."
        ],
        practical_utility: "Enables engineering teams to write once and expose their internal APIs and databases to any MCP-compliant agent framework.",
        ecosystem_impact: "De-facto standard for agent tool calling, mitigating vendor lock-in for enterprise AI deployments.",
        related_papers: [],
        related_entities: ["Anthropic", "Claude", "Cursor", "JSON-RPC"],
        tags: ["MCP", "Agents", "Tool Calling", "Interoperability", "Developer Tools"]
      }
    ],
    user_feedback: [{ rating: "good" }]
  },
  {
    id: "art-104",
    title: "FlashAttention-3: Fast and Memory-Efficient Exact Attention with FP8 Tensor Cores",
    clean_text: "FlashAttention-3 advances hardware-aware exact attention algorithms by targeting the specialized asynchronous tensor execution units on NVIDIA Hopper (H100/H800) GPUs. The paper introduces warp-specialized software pipelining that interleaves GEMM operations with softmax computation without stalling shared memory. By exploiting native FP8 Tensor Core instructions and hardware TMA (Tensor Memory Accelerator), FlashAttention-3 achieves up to 740 TFLOPs/s (up to 75% theoretical peak FLOPs utilization), yielding a 1.5x-2.0x speedup over FlashAttention-2.",
    url: "https://arxiv.org/abs/2407.08608",
    source_name: "arXiv cs.LG",
    published_at: new Date(Date.now() - 3600000 * 20).toISOString(),
    scraped_at: new Date(Date.now() - 3600000 * 15).toISOString(),
    classifications: [
      {
        id: "cls-104",
        category: "paper",
        subcategory: "Kernel Optimization",
        importance: 93,
        is_ai_relevant: true,
        technical_depth: "Deep Mathematical",
        reason: "Maximal hardware utilization on Hopper architecture; foundational optimization for long-context training and inference runs."
      }
    ],
    insights: [
      {
        id: "ins-104",
        headline: "Warp specialization and TMA integration drive FP8 exact attention to 75% of theoretical H100 compute ceiling.",
        tldr: [
          "Eliminates non-matmul FLOP bottlenecks by scheduling softmax computations asynchronously while MMA warps execute tile multiplication.",
          "Implements block quantization with per-tile scale factors to circumvent precision degradation in FP8 matrices.",
          "Substantially reduces self-attention execution time in contexts exceeding 64k tokens."
        ],
        practical_utility: "Accelerates pre-training iterations and reduces generation latency for long-context RAG and reasoning agents.",
        ecosystem_impact: "Now integrated into PyTorch, vLLM, and TensorRT-LLM as the default high-performance attention kernel.",
        related_papers: ["arXiv:2205.14135", "arXiv:2307.08691"],
        related_entities: ["Tri Dao", "NVIDIA", "Hopper TMA", "PyTorch"],
        tags: ["CUDA", "Attention", "FP8", "Hardware Acceleration", "TMA"]
      }
    ],
    user_feedback: []
  },
  {
    id: "art-105",
    title: "Claude 3.7 Sonnet: Hybrid Deliberative Architecture with Dynamic Thinking Budgets",
    clean_text: "Anthropic has released Claude 3.7 Sonnet, introducing a unified hybrid reasoning architecture that allows users to modulate the computational budget allocated to deliberate thinking on a per-request basis. Unlike separate reasoning and non-reasoning checkpoints, Claude 3.7 functions within a single continuous weight manifold capable of instantaneous execution or deep step-by-step chain-of-thought exploration up to 128,000 thinking tokens. Benchmark evaluations show state-of-the-art proficiency in competitive programming, full-stack software refactoring, and complex mathematical formalization.",
    url: "https://www.anthropic.com/claude/sonnet",
    source_name: "Anthropic News",
    published_at: new Date(Date.now() - 3600000 * 28).toISOString(),
    scraped_at: new Date(Date.now() - 3600000 * 22).toISOString(),
    classifications: [
      {
        id: "cls-105",
        category: "product",
        subcategory: "Frontier Foundation Models",
        importance: 94,
        is_ai_relevant: true,
        technical_depth: "System Whitepaper",
        reason: "First mainstream frontier model to merge fast conversational fluency with fine-grained controllable chain-of-thought reasoning tokens."
      }
    ],
    insights: [
      {
        id: "ins-105",
        headline: "Dynamic test-time compute budget parameter gives developers deterministic control over reasoning latency vs accuracy.",
        tldr: [
          "Users configure a max_thinking_tokens budget from 0 (instant response) up to 128k tokens for intractable debugging tasks.",
          "Maintains coherent internal monologue tracking invariants during large codebase refactoring without derailment.",
          "Achieves 70.3% on SWE-bench Verified in full thinking mode with agent scaffolding."
        ],
        practical_utility: "Enables production systems to route routine tasks with zero thinking overhead while reserving full reasoning depth for critical workflows.",
        ecosystem_impact: "Establishes controllable test-time compute as the primary paradigm for next-generation frontier intelligence.",
        related_papers: ["arXiv:2410.02498"],
        related_entities: ["Anthropic", "Claude 3.7", "SWE-bench", "RLHF"],
        tags: ["Reasoning", "Thinking Budget", "SWE-bench", "Test-time Compute", "Frontier Models"]
      }
    ],
    user_feedback: [{ rating: "good" }]
  },
  {
    id: "art-106",
    title: "Google Gemini 2.0 Flash: Multimodal Streaming Runtimes and Built-in Code Execution",
    clean_text: "Google DeepMind has made Gemini 2.0 Flash generally available, featuring native low-latency bidirectional multimodal streaming across audio, vision, and text. Built on a modernized sparse computation architecture, Gemini 2.0 Flash cuts time-to-first-token to under 180ms while expanding context window capacity to 1M tokens. The release introduces native tool orchestration, empowering the model to recursively generate, execute, and inspect Python code in an isolated sandbox environment before finalizing output responses.",
    url: "https://deepmind.google/technologies/gemini/flash/",
    source_name: "Google DeepMind",
    published_at: new Date(Date.now() - 3600000 * 36).toISOString(),
    scraped_at: new Date(Date.now() - 3600000 * 30).toISOString(),
    classifications: [
      {
        id: "cls-106",
        category: "product",
        subcategory: "Multimodal Systems",
        importance: 88,
        is_ai_relevant: true,
        technical_depth: "Architectural Spec",
        reason: "Significant step forward for real-time edge voice and video interaction with integrated runtime tool feedback loops."
      }
    ],
    insights: [
      {
        id: "ins-106",
        headline: "Sub-200ms audio-to-audio latency paired with self-directed code execution sandboxes.",
        tldr: [
          "Full multimodal audio and video stream tokens processed natively without intermediate Whisper or TTS transcoders.",
          "Sandbox execution environment allows iterative Python verification of calculations and data science queries.",
          "1M token context window maintained with high needle-in-a-haystack recall across mixed media."
        ],
        practical_utility: "Ideal for real-time customer support avatars, live video diagnostic agents, and complex coding co-pilots.",
        ecosystem_impact: "Forces competing frontier labs to adopt end-to-end multimodal architectures over bolted-on pipeline approaches.",
        related_papers: ["arXiv:2312.11805"],
        related_entities: ["Google", "DeepMind", "Gemini 2.0", "TPU v5p"],
        tags: ["Multimodal", "Streaming Audio", "Code Execution", "Gemini", "Low Latency"]
      }
    ],
    user_feedback: []
  },
  {
    id: "art-107",
    title: "SmolLM2: Advancing High-Efficiency Local SLMs for Edge Inference",
    clean_text: "Hugging Face has open-sourced the SmolLM2 family (135M, 360M, and 1.7B parameter checkpoints) engineered explicitly for local inference on mobile phones and embedded edge hardware. Trained on FineData-v2 (a curated 11-trillion token mixture of synthetic textbooks, filtered web data, and verified Python snippets), SmolLM2-1.7B achieves superior performance compared to older models quadruple its size on GSM8K and HumanEval benchmarks while operating comfortably within 1.2 GB of RAM under 4-bit GGUF quantization.",
    url: "https://huggingface.co/blog/smollm2",
    source_name: "The Batch",
    published_at: new Date(Date.now() - 3600000 * 48).toISOString(),
    scraped_at: new Date(Date.now() - 3600000 * 40).toISOString(),
    classifications: [
      {
        id: "cls-107",
        category: "paper",
        subcategory: "Small Language Models",
        importance: 85,
        is_ai_relevant: true,
        technical_depth: "Production Systems",
        reason: "Exemplifies data-filtering saturation for training sub-2B parameter models that run locally on consumer devices with negligible battery draw."
      }
    ],
    insights: [
      {
        id: "ins-107",
        headline: "1.7B parameter model beats original LLaMA-7B across code synthesis and reasoning via synthetic data curriculum.",
        tldr: [
          "11T token pre-training mixture heavily prioritized clean educational content and step-by-step code rationale.",
          "4-bit quantization allows full context execution within edge devices such as Raspberry Pi 5 and iPhone 15.",
          "Fully open Apache 2.0 weights with dataset recipe documentation."
        ],
        practical_utility: "Enables offline on-device privacy-preserving AI applications with zero cloud egress costs.",
        ecosystem_impact: "Proves that data curation quality outweighs raw parameter count for task-specific edge deployments.",
        related_papers: ["arXiv:2407.10671"],
        related_entities: ["Hugging Face", "SmolLM", "GGUF", "llama.cpp"],
        tags: ["SLM", "On-Device AI", "Quantization", "Edge Computing", "Hugging Face"]
      }
    ],
    user_feedback: []
  },
  {
    id: "art-108",
    title: "OpenAI Operator: Autonomous Computer-Using Agent Architecture and Sandbox Safeguards",
    clean_text: "OpenAI has previewed Operator, an autonomous browser and GUI execution agent capable of planning and performing complex multi-step workflows across native software applications and web portals. The agent combines high-resolution visual grounding with browser DOM parsing, generating low-level keyboard and mouse primitives. To mitigate security hazards like prompt injection in wild web environments, Operator incorporates isolated sandboxed browsing runtimes with user-in-the-loop confirmation gates for high-stakes financial and authentication steps.",
    url: "https://openai.com/index/operator-announcement/",
    source_name: "OpenAI Blog",
    published_at: new Date(Date.now() - 3600000 * 60).toISOString(),
    scraped_at: new Date(Date.now() - 3600000 * 52).toISOString(),
    classifications: [
      {
        id: "cls-108",
        category: "product",
        subcategory: "Autonomous Agents",
        importance: 91,
        is_ai_relevant: true,
        technical_depth: "System Whitepaper",
        reason: "Milestone in browser automation agents utilizing unified vision-DOM multimodal foundations and containment architecture."
      }
    ],
    insights: [
      {
        id: "ins-108",
        headline: "Vision-DOM fusion agent executes complex multistep web workflows with human-in-the-loop security boundaries.",
        tldr: [
          "Coordinates visual screenshot understanding with live accessibility DOM trees to interact with dynamic web elements.",
          "Incorporates automated backtracking and self-recovery when visual layout shifts unexpectedly during form submissions.",
          "Hardened against prompt injections hidden in external page content through dual-model supervisory filtering."
        ],
        practical_utility: "Automates legacy enterprise web workflows that lack programmatic API endpoints.",
        ecosystem_impact: "Accelerates commercial race toward practical general-purpose computer use agents.",
        related_papers: ["arXiv:2401.13649"],
        related_entities: ["OpenAI", "Playwright", "Computer Use", "WebAgent"],
        tags: ["Agents", "Computer Use", "Automation", "Security", "Browser Sandbox"]
      }
    ],
    user_feedback: []
  }
];

export const MOCK_SOURCES = [
  {
    id: "src-001",
    name: "arXiv cs.AI (Artificial Intelligence)",
    url: "http://export.arxiv.org/rss/cs.AI",
    type: "rss",
    category: "arxiv",
    active: true,
    last_scraped: new Date(Date.now() - 3600000 * 2).toISOString(),
    scrape_config: { refresh_interval_min: 60 }
  },
  {
    id: "src-002",
    name: "arXiv cs.LG (Machine Learning)",
    url: "http://export.arxiv.org/rss/cs.LG",
    type: "rss",
    category: "arxiv",
    active: true,
    last_scraped: new Date(Date.now() - 3600000 * 2).toISOString(),
    scrape_config: { refresh_interval_min: 60 }
  },
  {
    id: "src-003",
    name: "OpenAI Engineering & Research Blog",
    url: "https://openai.com/blog/rss.xml",
    type: "rss",
    category: "company",
    active: true,
    last_scraped: new Date(Date.now() - 3600000 * 4).toISOString(),
    scrape_config: { refresh_interval_min: 120 }
  },
  {
    id: "src-004",
    name: "Anthropic Research News",
    url: "https://www.anthropic.com/feed.xml",
    type: "rss",
    category: "company",
    active: true,
    last_scraped: new Date(Date.now() - 3600000 * 3).toISOString(),
    scrape_config: { refresh_interval_min: 120 }
  },
  {
    id: "src-005",
    name: "Google DeepMind Publications",
    url: "https://deepmind.google/blog/rss.xml",
    type: "rss",
    category: "company",
    active: true,
    last_scraped: new Date(Date.now() - 3600000 * 5).toISOString(),
    scrape_config: { refresh_interval_min: 120 }
  },
  {
    id: "src-006",
    name: "The Batch (DeepLearning.AI)",
    url: "https://www.deeplearning.ai/the-batch/feed/",
    type: "rss",
    category: "newsletter",
    active: true,
    last_scraped: new Date(Date.now() - 3600000 * 8).toISOString(),
    scrape_config: { refresh_interval_min: 240 }
  },
  {
    id: "src-007",
    name: "TLDR AI Technical Digest",
    url: "https://tldr.tech/ai/rss",
    type: "rss",
    category: "newsletter",
    active: true,
    last_scraped: new Date(Date.now() - 3600000 * 6).toISOString(),
    scrape_config: { refresh_interval_min: 180 }
  },
  {
    id: "src-008",
    name: "Import AI (Jack Clark)",
    url: "https://importai.substack.com/feed",
    type: "rss",
    category: "newsletter",
    active: true,
    last_scraped: new Date(Date.now() - 3600000 * 10).toISOString(),
    scrape_config: { refresh_interval_min: 360 }
  }
];

export const MOCK_HEALTH_DATA = [
  {
    id: "health-001",
    run_id: "80f3c975-a3be-4ec8-9526-001d531c63d0",
    health_score: 0.96,
    sources_successful: 8,
    sources_total: 8,
    new_signals: 12,
    llm_success_rate: 0.98,
    created_at: new Date(Date.now() - 3600000 * 1).toISOString(),
    pipeline_runs: {
      ingested: 168,
      embedded: 164,
      duplicates: 38,
      duration_s: 21
    }
  },
  {
    id: "health-002",
    run_id: "67a2b910-b4ec-4f12-8821-229d442c55e1",
    health_score: 0.92,
    sources_successful: 8,
    sources_total: 8,
    new_signals: 9,
    llm_success_rate: 0.95,
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
    pipeline_runs: {
      ingested: 142,
      embedded: 139,
      duplicates: 29,
      duration_s: 18
    }
  },
  {
    id: "health-003",
    run_id: "54c1e809-c1dd-4a33-9110-118e331b44d9",
    health_score: 0.89,
    sources_successful: 7,
    sources_total: 8,
    new_signals: 14,
    llm_success_rate: 0.93,
    created_at: new Date(Date.now() - 3600000 * 9).toISOString(),
    pipeline_runs: {
      ingested: 189,
      embedded: 185,
      duplicates: 44,
      duration_s: 26
    }
  },
  {
    id: "health-004",
    run_id: "42b0d798-d0cc-4922-8009-007d220a33c8",
    health_score: 0.94,
    sources_successful: 8,
    sources_total: 8,
    new_signals: 11,
    llm_success_rate: 0.97,
    created_at: new Date(Date.now() - 3600000 * 14).toISOString(),
    pipeline_runs: {
      ingested: 155,
      embedded: 151,
      duplicates: 32,
      duration_s: 19
    }
  }
];
