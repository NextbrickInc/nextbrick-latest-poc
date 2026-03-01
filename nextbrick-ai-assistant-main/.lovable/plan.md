

# Agentic AI POC Dashboard

## Design System
- Primary color: Sky blue accent
- Warm neutral backgrounds with clean white cards
- Bold typography hierarchy, enterprise-grade spacing

## Page Structure

### 1. Hero Section
- "Recommendation: Nextbrick Solution" headline with subtitle
- Professional gradient banner with sky blue accent

### 2. Demo Toggle (On-Prem vs Cloud)
- Prominent toggle/tab switcher between the two demos
- **On-Prem**: Mac Studio, Santa Clara — gpt-oss-20b, bge-m3, Elasticsearch OSS, Kafka, Spark, LangChain/LangGraph
- **Cloud**: Elastic Cloud (GCP) — Claude Sonnet 4.5
- Each demo shows its tech stack badges

### 3. KPI Cards Row
- Indexed Docs: 5,000
- Languages: 4–8
- Target QPS: 20–30
- Latency: <2s

### 4. Interactive Panels (Side-by-Side Layout)
- **Chatbot Panel**: Multi-turn conversation UI with sample prompts (e.g., "Find product specs in German", "Summarize Q3 pipeline")
- **Search Results Panel**: AI-generated summaries with citation badges and source links

### 5. Tool Call Status Panel
- Status cards for Salesforce, Confluence, AEM DAM with connection indicators and mock latency

### 6. Scope & Out-of-Scope Sections
- Two-column card layout listing what's in scope vs excluded

### 7. Key Deliverables
- Checklist-style list of project deliverables

### 8. Test Case Validation
- Table/cards for 6 test cases with pass/fail status indicators

### 9. Metrics Comparison Table
- Paid vs OSS comparison: tokens in/out, setup time, LLM latency, ES latency, tool calls, accuracy

