# **Technical Architecture Report: The Google Interactions API and the Shift to Stateful Agent Orchestration**

## **1\. Executive Summary and Architectural Context**

The release of the Google Interactions API in December 2025 represents a fundamental architectural pivot in the design and deployment of Large Language Model (LLM) applications. For the past several years, the dominant paradigm for integrating generative AI into backend systems has been stateless inference. In this legacy model, exemplified by endpoints such as generateContent, the responsibility for state management, context window optimization, and conversation history persistence rested entirely on the client application.1 While sufficient for simple request-response cycles, this architecture creates significant bottlenecks for complex, multi-turn agentic workflows: excessive network bandwidth consumption due to repetitive context transmission, increased latency from re-processing static tokens, and brittle client-side logic for tool orchestration.

The Interactions API (/interactions) addresses these systemic inefficiencies by introducing a stateful, server-side primitive for LLM sessions. By elevating the "Interaction" to a first-class resource, Google allows backend engineers to offload the cognitive architecture of agents—memory, planning, and tool execution—to the cloud infrastructure.3 This shift is not merely syntactic; it enables the deployment of autonomous agents, such as the Gemini Deep Research agent, which can execute long-running asynchronous tasks spanning minutes or hours without requiring a persistent open connection from the client.5

Furthermore, the integration of the Model Context Protocol (MCP) fundamentally standardizes how these models connect to external data and tools, moving away from proprietary function-calling schemas toward an open, interoperable standard.6 This report provides an exhaustive technical analysis of the Interactions API, detailing the API contract, persistence mechanisms, asynchronous polling architectures, MCP integration strategies, and the operational economics of migrating from stateless to stateful AI systems.

## ---

**2\. The API Contract: Semantic Structure and Payload Analysis**

The core interface for this new paradigm is the /interactions endpoint. Unlike its predecessors, which were designed primarily for text generation, this endpoint is polymorphic, capable of handling synchronous chat, asynchronous agent execution, and multimodal input streams within a unified schema. Understanding the nuance of this contract is critical for backend engineers designing the integration layer.

### **2.1 The Polymorphic Nature of Interactions**

The endpoint accepts a JSON payload that varies significantly depending on the intended target—a raw model (e.g., gemini-3-pro-preview) or a managed agent (e.g., deep-research-pro-preview-12-2025). This design unifies the developer experience, allowing a single client SDK to switch between standard inference and complex agentic work with minimal refactoring.2

When initiating a session, the input field demonstrates this flexibility. It can accept a simple string for quick prototyping, a structured list of Content objects for multimodal inputs (interleaving text, images, and audio), or a list of Turn objects for stateless operations where the client still manages history.8 However, the primary utility of this API lies in its stateful mode, triggered by the store parameter.

### **2.2 Initiating a Synchronous Model Session**

For standard conversational applications—chatbots, coding assistants, or interactive data analysts—the interaction is typically synchronous. The client sends a prompt, and the server maintains the connection open until the generation is complete. The crucial difference from legacy APIs is the store: true default, which triggers the creation of a server-side session.

**Technical Specification: Synchronous Request**

The following JSON payload illustrates the initiation of a session with the Gemini 3 Pro model. Note the explicit configuration for store, which ensures that the conversation history is persisted for subsequent turns.

JSON

{  
  "model": "gemini-3-pro-preview",  
  "input": {  
    "role": "user",  
    "parts": \[  
      {  
        "text": "Analyze the provided system logs and identify the root cause of the latency spike."  
      }  
    \]  
  },  
  "tools": \[  
    {  
      "google\_search": {}   
    }  
  \],  
  "config": {  
    "temperature": 0.2,  
    "store": true  
  }  
}

**Implementation via google-genai Python SDK**

The Python SDK abstracts the raw REST calls, providing a typed interface for interaction creation. The snippet below demonstrates how to initialize the client and create the first turn of a conversation.

Python

from google import genai  
from google.genai import types

\# Initialize the client with the API key from the environment  
client \= genai.Client(api\_key="YOUR\_GEMINI\_API\_KEY")

\# Create the interaction targeting a specific model  
interaction \= client.interactions.create(  
    model="gemini-3-pro-preview",  
    input\="Analyze the system logs for the payment gateway service.",  
    config=types.InteractionConfig(  
        store=True, \# Persist state server-side  
        tools=  
    )  
)

\# Accessing the response and the session ID  
print(f"Interaction ID: {interaction.id}")  
print(f"Response: {interaction.outputs\[-1\].text}")

3

In this implementation, the interaction.id returned in the response object is the critical artifact. It is the handle by which the client will reference this specific conversational context in all future requests. Unlike the chat\_session objects in older SDKs which stored history in client memory, this ID references a remote resource.2

### **2.3 Initiating an Asynchronous Agent Session**

The API contract changes when targeting an agent designed for long-running tasks, such as Gemini Deep Research. These agents perform iterative loops of thought, search, and synthesis that effectively preclude synchronous HTTP connections due to timeout risks.

**Technical Specification: Asynchronous Request**

For these scenarios, the background parameter is mandatory. This instructs the API to detach the processing from the HTTP response. The server acknowledges receipt of the task immediately but returns an interaction object with a status of IN\_PROGRESS.5

**CURL Example for Deep Research**

Bash

curl \-X POST "https://generativelanguage.googleapis.com/v1beta/interactions?key=$GEMINI\_API\_KEY" \\  
\-H "Content-Type: application/json" \\  
\-d '{  
  "agent": "deep-research-pro-preview-12-2025",  
  "input": "Conduct a comprehensive due diligence report on the adoption of RISC-V architecture in the automotive sector, focusing on thermal management systems.",  
  "background": true,  
  "store": true  
}'

The payload differences are subtle but significant:

1. **agent vs. model:** The agent field specifies a managed system (e.g., deep-research-pro-preview-12-2025) rather than a raw model.2  
2. **background: true:** This flag dictates the async behavior. Without it, a request to a Deep Research agent might time out or be rejected.5  
3. **store: true:** This is implicitly required for background tasks, as the client needs a persistent resource to poll against.5

The return payload for this request does not contain the answer. Instead, it provides the metadata necessary to monitor the job:

JSON

{  
  "id": "int\_1234567890abcdef",  
  "status": "in\_progress",  
  "created": "2025-12-17T12:00:00Z",  
  "outputs":  
}

This decoupling of request and response allows the backend engineer to design resilient architectures that are robust to network interruptions and client restarts, a requirement for enterprise-grade agent deployment.10

## ---

**3\. Server-Side State Management: Persistence and Flow**

The defining characteristic of the Interactions API is its move to server-side state. In the legacy generateContent model, the "state" of a conversation was simply the accumulation of tokens in the prompt. This statelessness meant that for a conversation with 50 turns, the 50th request involved re-transmitting the previous 49 turns, incurring redundant bandwidth costs and processing latency.

### **3.1 The Mechanics of Persistence**

When an interaction is created with store=true, Google persists the interaction tree—the sequence of user inputs, model outputs, tool calls, and intermediate "thoughts"—in its infrastructure.2 This persistence layer serves as a remote memory bank for the application.

Data Retention and Privacy:  
Backend engineers must be cognizant of the data lifecycle in this model.

* **Free Tier:** Interaction data is retained for 24 hours.  
* **Paid Tier:** Data is retained for up to 55 days.2  
* **Control:** The API supports explicit deletion methods (DELETE /interactions/{id}), allowing applications to implement their own retention policies for GDPR or CCPA compliance.  
* **Opt-out:** Setting store=false reverts to stateless behavior, but disables features like background execution and referencing previous IDs.8

### **3.2 The Linked-List Flow of Multi-Turn Conversations**

The implementation of a chat interface shifts from managing a list of messages to managing a pointer to the latest interaction ID. Each new turn in the conversation is a new create request that points to the tail of the previous interaction.

**Flow Description:**

1. **Turn 1 (Root):** The client sends the initial prompt P1. The server creates Interaction I1 containing \`\`. The server returns I1's ID.  
2. **Turn 2 (Leaf):** The user provides follow-up P2. The client sends P2 and previous\_interaction\_id=I1. The server retrieves the context of I1, appends P2, generates Response2, and saves this new state as Interaction I2.  
3. **Turn 3 (Leaf):** The client sends P3 and previous\_interaction\_id=I2.

This structure effectively creates a linked list or a directed acyclic graph (DAG) of conversation states. It enables powerful features like "branching," where a user can go back to I1 and provide an alternative prompt P2\_beta, creating a new branch I2\_beta without destroying the original I2.8

**Python Implementation of the Stateful Flow:**

Python

def run\_stateful\_chat\_session():  
    """  
    Demonstrates a multi-turn conversation loop using the Interactions API.  
    """  
    client \= genai.Client()  
    current\_interaction\_id \= None  
      
    print("--- Starting Stateful Session \---")  
      
    while True:  
        user\_input \= input("User: ")  
        if user\_input.lower() in \["exit", "quit"\]:  
            break

        \# Construct parameters for the API call  
        \# Note: We only send the \*new\* input and the reference ID.  
        request\_params \= {  
            "model": "gemini-3-pro-preview",  
            "input": user\_input,  
            "config": types.InteractionConfig(store=True)  
        }  
          
        \# If this is not the first turn, link to the previous history  
        if current\_interaction\_id:  
            request\_params\["previous\_interaction\_id"\] \= current\_interaction\_id

        try:  
            \# Execute the interaction  
            response \= client.interactions.create(\*\*request\_params)  
              
            \# Update the state pointer to the new head of the chain  
            current\_interaction\_id \= response.id  
              
            \# Extract and display the model's text response  
            \# The 'outputs' list contains the response for \*this specific turn\*  
            model\_text \= response.outputs\[-1\].text  
            print(f"Gemini: {model\_text}")  
              
        except Exception as e:  
            print(f"Session Error: {e}")  
            break

2

### **3.3 Context Compression and Optimization**

A significant advantage of server-side state is the optimization of the context window. When the conversation history exceeds the model's token limit (e.g., 1 million or 2 million tokens), the legacy client-side approach required complex logic to summarize or truncate old messages. The Interactions API handles this "Context Compression" automatically using a sliding window mechanism tailored to the specific model.1

This mechanism preserves the system\_instruction and the most recent relevant turns while intelligently discarding or summarizing intermediate history. This reduces the engineering burden on the backend team, ensuring that "context length exceeded" errors are handled gracefully by the platform rather than crashing the application.1

## ---

**4\. Asynchronous Orchestration: The Deep Research Pattern**

The introduction of the **Gemini Deep Research** agent necessitates an asynchronous interaction pattern. This agent does not merely generate text; it autonomously plans research strategies, executes parallel search queries, reads document content, synthesizes findings, and iterates on its hypothesis.5 This process is computationally intensive and temporally extended, often running for 20 to 60 minutes.5

### **4.1 The Background Execution Model**

When background=true is invoked, the Interactions API behaves like a job queue. The immediate response confirms that the job has been accepted. The backend engineer must then implement a robust polling mechanism to retrieve the final result.

**State Transitions:**

* **IN\_PROGRESS:** The agent is actively working (planning, searching, reading).  
* **COMPLETED:** The task has finished successfully, and the report is available in the outputs field.  
* **FAILED:** The agent encountered an unrecoverable error (e.g., safety filters, internal timeouts).  
* **REQUIRES\_ACTION:** The agent needs human intervention or additional tool permissions (though Deep Research is currently fully autonomous).5

### **4.2 Implementing Robust Polling Logic**

Polling for long-running tasks requires careful implementation to avoid rate limits and unnecessary network traffic. A linear polling interval (e.g., every 5 seconds) is inefficient for tasks that take 30 minutes. An exponential backoff strategy is recommended.

**Python Implementation of Polling with Backoff:**

Python

import time  
from google import genai

def run\_deep\_research\_task(topic):  
    client \= genai.Client()

    print(f"Submitting research task for: {topic}")  
      
    \# 1\. Submit the background job  
    interaction \= client.interactions.create(  
        agent="deep-research-pro-preview-12-2025",  
        input\=f"Research technical specifications and market analysis for: {topic}",  
        background=True  
    )  
      
    task\_id \= interaction.id  
    print(f"Task ID: {task\_id}. Beginning polling...")

    \# 2\. Define polling parameters  
    poll\_interval \= 10  \# Start with 10 seconds  
    max\_interval \= 60   \# Cap at 60 seconds  
      
    while True:  
        \# Retrieve the current state of the interaction resource  
        current\_state \= client.interactions.get(id\=task\_id)  
        status \= current\_state.status

        if status \== "completed":  
            \# Success: Extract the final report  
            report \= current\_state.outputs\[-1\].text  
            print("\\n--- Research Complete \---")  
            print(report)  
            return report  
          
        elif status \== "failed":  
            \# Failure: Log the error details  
            print(f"\\nTask Failed. Error: {current\_state.error}")  
            break  
              
        elif status \== "cancelled":  
            print("\\nTask was cancelled.")  
            break  
              
        elif status \== "in\_progress":  
             \# Wait and retry  
             print(f"Status: {status}. Waiting {poll\_interval}s...")  
             time.sleep(poll\_interval)  
               
             \# Implement slight backoff for long-running tasks  
             poll\_interval \= min(poll\_interval \+ 5, max\_interval)  
          
        else:  
            print(f"Unknown status: {status}")  
            time.sleep(10)

5

### **4.3 Streaming in Background**

To improve the user experience during long wait times, the Interactions API supports streaming *even for background tasks*. By setting stream=true in conjunction with background=true, the client can open a persistent connection to receive real-time updates on the agent's progress.5

These updates might include "Thought" events (e.g., "I need to verify the release date of the library") or "Tool Use" events (e.g., "Searching Google for..."). This transparency is crucial for user trust. The API implements a **resumable stream** pattern: if the connection drops, the client can reconnect using the last\_event\_id parameter to receive only the events that occurred during the disconnection, ensuring no data loss in the audit trail.5

## ---

**5\. Model Context Protocol (MCP): Standardization of Tooling**

One of the most transformative aspects of the Interactions API is its native support for the **Model Context Protocol (MCP)**. MCP is an open standard that standardizes how AI agents interface with external systems. Before MCP, connecting an LLM to a database or a file system required bespoke "glue code" for every integration—defining JSON schemas, parsing model outputs, executing SQL locally, and handling errors. MCP eliminates this fragmentation.6

### **5.1 The MCP Architecture**

MCP operates on a client-host-server architecture:

1. **MCP Host:** The AI application (in this case, the Gemini Interactions API/Client).  
2. **MCP Server:** A standalone service that exposes "Resources" (data) and "Tools" (functions) via a standardized protocol.  
3. **MCP Client:** The connector that bridges the Host and Server.

In the Interactions API ecosystem, the backend engineer does not need to manually write function declarations. Instead, they configure an **MCP Toolset** that connects to an MCP Server. The SDK automatically queries the server for its capabilities (ListTools), translates them into the Gemini-compatible schema, and handles the execution routing.13

### **5.2 Defining an MCP Tool: Code Example**

The following example demonstrates how to integrate a local MCP server (specifically, a filesystem server) into a Gemini session. This allows the model to read and write files on the local machine securely.

**Python Implementation using google-genai and adk:**

Python

import os  
from google.genai import Client  
from google.adk.tools.mcp\_tool import McpToolset  
from google.adk.tools.mcp\_tool.mcp\_session\_manager import StdioConnectionParams  
from mcp import StdioServerParameters

\# 1\. Define the connection to the MCP Server  
\# In this case, we are launching a local Node.js process that implements the MCP protocol  
\# for filesystem access.  
server\_params \= StdioServerParameters(  
    command="npx",  
    args=  
)

\# 2\. Initialize the MCP Toolset  
\# This wrapper manages the stdio communication with the sub-process.  
filesystem\_mcp \= McpToolset(  
    connection\_params=StdioConnectionParams(  
        server\_params=server\_params  
    ),  
    \# Security Best Practice: Explicitly allow-list the tools exposed to the model  
    tool\_filter=\['read\_file', 'list\_directory'\]   
)

\# 3\. Initialize the Gemini Client  
client \= Client(api\_key=os.environ)

\# 4\. Create the Interaction  
\# The SDK handles the handshake: querying the MCP server for tool definitions  
\# and injecting them into the API request.  
response \= client.interactions.create(  
    model="gemini-3-pro-preview",  
    input\="List the files in the current directory and read the content of 'server\_config.yaml'.",  
    tools=\[filesystem\_mcp\], \# Pass the toolset directly  
    config={"store": True}  
)

\# The result contains the model's synthesis of the file content,   
\# retrieved via the MCP tool execution.  
print(response.outputs\[-1\].text)

13

### **5.3 Managed vs. Custom MCP Servers**

Backend engineers have two deployment options for MCP:

1. **Local/Custom MCP:** As shown above, the McpToolset runs a local process (stdio) or connects to a remote URL (SSE). This is ideal for bespoke tools or internal APIs.  
2. **Google Managed MCP:** Google provides fully managed MCP servers for its own ecosystem (Google Maps, BigQuery, Google Search). These are configured via simple references in the API call or settings files, eliminating the need to host a separate server process. For example, the Google Maps MCP server allows the agent to perform geospatial reasoning without the developer managing the Maps API keys directly in the tool logic.14

Security Implications:  
When using Custom MCP servers, the security boundary shifts. The Interactions API acts as a conduit, but the execution of the tool happens on the MCP server. If an MCP server exposes a "delete database" tool, the model can invoke it. Therefore, strict access controls and tool\_filter lists are mandatory in production environments.15

## ---

**6\. Comparative Analysis: generateContent vs. /interactions**

The decision to migrate from the stateless generateContent API to the stateful /interactions API involves distinct trade-offs regarding latency, cost, and implementation complexity. The following table summarizes these differences for the backend architect.

### **6.1 Comparison Matrix**

| Feature Domain | Stateless (generateContent) | Stateful (/interactions) | Implications for Backend Engineering |
| :---- | :---- | :---- | :---- |
| **State Management** | **Client-Side:** The application DB stores the full chat history. Every request re-transmits the entire context stack. | **Server-Side:** The application stores only the interaction\_id. Requests send only the new user input (delta). | **Bandwidth:** Drastic reduction in egress traffic. **Storage:** Simplifies client-side DB schema (no need to store message blobs). |
| **Latency** | **High & Variable:** Time-To-First-Token (TTFT) increases linearly with conversation length as the model re-processes input tokens. | **Low & Constant:** Server-side caching means the history is already "hot" in memory. TTFT remains low even for long sessions. | **UX:** Significantly snappier responses for deep conversations or RAG applications with large contexts. |
| **Cost Model** | **Redundant:** You pay for input tokens of the *entire history* on every turn. | **Optimized:** You pay for *storage* (cache duration) and *new* input tokens only. | **Economics:** Cheaper for frequent, multi-turn interactions. Potentially pricier for sparse interactions due to storage/retention fees. |
| **Concurrency** | **Synchronous:** The HTTP connection must be held open for the duration of generation. | **Async Capable:** background=true enables "fire-and-forget" patterns for long tasks. | **Reliability:** Eliminates HTTP timeout errors (504 Gateway Timeout) for reasoning-heavy tasks (Deep Research). |
| **Tooling (MCP)** | **Manual Glue:** Developer must parse JSON, execute code locally, and inject results back into the prompt loop. | **Native Integration:** The SDK/API handles the tool handshake via MCP standards. | **Maintenance:** Reduces boilerplate code. Decouples tool implementation from agent logic. |
| **Agent Support** | **Custom Only:** Developers must build their own "ReAct" loops or usage chains. | **First-Class:** Access to managed agents like Deep Research (Gemini 3 Pro reasoning). | **Capability:** Unlocks capabilities (autonomous research) that are impossible to implement purely client-side. |

2

### **6.2 Economic Analysis of State**

The cost implications of the /interactions API are nuanced. While generateContent charges for processed input tokens (which grow cumulatively), /interactions introduces a **Context Caching Price** model.

* **Storage Cost:** There is an hourly cost for storing the active context (e.g., $4.50 / 1M tokens per hour).18  
* **Compute Cost:** You pay significantly less for input tokens because cached tokens are billed at a fraction of the standard rate (e.g., $0.125 vs $1.25 for paid tier Gemini 2.5 Pro).18

**Break-even Point:** Migration is economically favorable for applications with high interaction density (e.g., a user interacting with a document multiple times within an hour). For sporadic interactions (e.g., one question every 24 hours), the storage cost might outweigh the token savings, unless the session is explicitly terminated.

## ---

**7\. Operational Recommendations and Best Practices**

To successfully deploy the Interactions API in a production environment, several operational strategies should be adopted.

### **7.1 Architecture Patterns: The ADK Integration**

Google's **Agent Development Kit (ADK)** provides two primary patterns for integrating with the Interactions API 19:

1. **Inference Engine Pattern:** The ADK agent runs on your infrastructure but uses /interactions as its "brain." This allows you to keep control logic (routing, guardrails) local while offloading memory and context management to Google. This is the "Pattern 1" described in ADK documentation and is recommended for enterprise applications requiring strict governance.  
2. **Remote Agent Pattern (A2A):** The Interactions API endpoint is treated as a remote agent within an Agent-to-Agent (A2A) mesh. The InteractionsApiTransport layer translates A2A protocol messages into API calls. This is ideal for multi-agent systems where a specialized Google agent (like Deep Research) acts as a sub-worker for a master orchestrator.19

### **7.2 Testing and Observability**

* **Mocking Interaction IDs:** In integration tests, mock the interaction\_id to test state transitions without incurring API costs. Verify that your application correctly handles invalid or expired IDs (e.g., returning a 404/410 to the user and prompting a new session).  
* **Observability:** Since state is remote, traditional logging of "messages sent" is insufficient. Implement logging for interaction\_id and turn\_id to correlate client-side logs with Google's server-side audit trails.8  
* **Graceful Degrade:** Implement fallbacks for the polling loop. If the Deep Research agent is stuck in IN\_PROGRESS for \>60 minutes (the hard limit), the application should time out and alert the user rather than polling indefinitely.5

## **8\. Conclusion**

The Google Interactions API represents the maturity of the generative AI stack. It acknowledges that for LLMs to become true system components, they must possess state, agency, and standardized interfaces. For the backend engineer, the migration to /interactions offers a path to build more capable, faster, and cheaper agentic workflows. By leveraging server-side persistence, asynchronous orchestration for deep reasoning, and the interoperability of MCP, developers can focus on defining the *capabilities* of their agents rather than managing the plumbing of their conversations. The shift from stateless token generation to stateful interaction is not just an optimization; it is the prerequisite for the next generation of autonomous software.

#### **Works cited**

1. Release notes | Gemini API \- Google AI for Developers, accessed December 17, 2025, [https://ai.google.dev/gemini-api/docs/changelog](https://ai.google.dev/gemini-api/docs/changelog)  
2. Google Interactions API: The 2025 Guide to Unified Gemini Models ..., accessed December 17, 2025, [https://www.xugj520.cn/en/archives/google-interactions-api-guide-2.html](https://www.xugj520.cn/en/archives/google-interactions-api-guide-2.html)  
3. Interactions API: A unified foundation for models and agents \- Google Blog, accessed December 17, 2025, [https://blog.google/technology/developers/interactions-api/](https://blog.google/technology/developers/interactions-api/)  
4. Google Introduces Interactions API for Gemini Models \- AI Daily, accessed December 17, 2025, [https://www.ai-daily.news/articles/google-introduces-interactions-api-for-gemini-models](https://www.ai-daily.news/articles/google-introduces-interactions-api-for-gemini-models)  
5. Gemini Deep Research Agent | Gemini API \- Google AI for Developers, accessed December 17, 2025, [https://ai.google.dev/gemini-api/docs/deep-research](https://ai.google.dev/gemini-api/docs/deep-research)  
6. Code execution with MCP: building more efficient AI agents \- Anthropic, accessed December 17, 2025, [https://www.anthropic.com/engineering/code-execution-with-mcp](https://www.anthropic.com/engineering/code-execution-with-mcp)  
7. What is Model Context Protocol (MCP)? A guide \- Google Cloud, accessed December 17, 2025, [https://cloud.google.com/discover/what-is-model-context-protocol](https://cloud.google.com/discover/what-is-model-context-protocol)  
8. Interactions API | Gemini API \- Google AI for Developers, accessed December 17, 2025, [https://ai.google.dev/gemini-api/docs/interactions](https://ai.google.dev/gemini-api/docs/interactions)  
9. Interactions API \- Gemini API | Google AI for Developers, accessed December 17, 2025, [https://ai.google.dev/api/interactions-api](https://ai.google.dev/api/interactions-api)  
10. Google Rolls Out Interactions API for Next-Gen AI Agents \- The Rift, accessed December 17, 2025, [https://www.therift.ai/news-feed/google-rolls-out-interactions-api-for-next-gen-ai-agents](https://www.therift.ai/news-feed/google-rolls-out-interactions-api-for-next-gen-ai-agents)  
11. Google opens updated Deep Research Agent to developers with new API \- The Decoder, accessed December 17, 2025, [https://the-decoder.com/google-opens-updated-deep-research-agent-to-developers-with-new-api/](https://the-decoder.com/google-opens-updated-deep-research-agent-to-developers-with-new-api/)  
12. What is the Model Context Protocol (MCP)? Complete Guide to MCP Architecture, Servers, Clients & AI Integration, accessed December 17, 2025, [https://vishalbulbule.medium.com/what-is-the-model-context-protocol-mcp-59422d88ed85](https://vishalbulbule.medium.com/what-is-the-model-context-protocol-mcp-59422d88ed85)  
13. MCP tools \- Agent Development Kit \- Google, accessed December 17, 2025, [https://google.github.io/adk-docs/tools-custom/mcp-tools/](https://google.github.io/adk-docs/tools-custom/mcp-tools/)  
14. Announcing official MCP support for Google services | Google Cloud Blog, accessed December 17, 2025, [https://cloud.google.com/blog/products/ai-machine-learning/announcing-official-mcp-support-for-google-services](https://cloud.google.com/blog/products/ai-machine-learning/announcing-official-mcp-support-for-google-services)  
15. Building MCP servers for ChatGPT and API integrations \- OpenAI Platform, accessed December 17, 2025, [https://platform.openai.com/docs/mcp](https://platform.openai.com/docs/mcp)  
16. Vertex AI Pricing | Google Cloud, accessed December 17, 2025, [https://cloud.google.com/vertex-ai/generative-ai/pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)  
17. Submodules \- Google Gen AI SDK documentation, accessed December 17, 2025, [https://googleapis.github.io/python-genai/genai.html](https://googleapis.github.io/python-genai/genai.html)  
18. Gemini Developer API pricing, accessed December 17, 2025, [https://ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing)  
19. Building agents with the ADK and the new Interactions API \- Google ..., accessed December 17, 2025, [https://developers.googleblog.com/building-agents-with-the-adk-and-the-new-interactions-api/](https://developers.googleblog.com/building-agents-with-the-adk-and-the-new-interactions-api/)