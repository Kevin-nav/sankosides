# **The Architect’s Guide to the Gemini Interactions API: Stateful Agentic Systems with Gemini 3 Pro and Flash**

## **1\. Introduction: The Paradigm Shift in Generative Integration**

The release of the Gemini 3 model family—comprising the reasoning-dense Gemini 3 Pro and the latency-optimized Gemini 3 Flash—marks a seminal moment in the trajectory of Large Language Model (LLM) integration. However, the models themselves are only half of the narrative. The concurrent introduction of the **Interactions API** within the Google AI Studio ecosystem represents a fundamental architectural pivot from stateless, transactional inference to stateful, persistent agentic environments. This transition is not merely syntactic; it is a structural response to the limitations of previous generation LLM applications, which were plagued by context drift, cumbersome history management, and the inability to execute long-horizon tasks autonomously.1

For developers and systems architects operating within the Google AI Studio environment, strictly independent of the Vertex AI enterprise stack, this shift necessitates a complete re-evaluation of integration patterns. The legacy generateContent methods, while still functional for simple completions, are insufficient for accessing the advanced cognitive capabilities of Gemini 3\. Features such as "Thinking" (internal chain-of-thought processing), "Deep Research" (autonomous multi-step investigation), and cryptographic state verification via "Thought Signatures" are exclusively or optimally supported through the Interactions API.3

This report provides an exhaustive, expert-level technical analysis of this new infrastructure. It deconstructs the Interactions API into its atomic components, analyzes the specific behaviors of Gemini 3 Pro and Flash within this framework, and provides a definitive guide to implementing stateful, grounded, and autonomous systems. The analysis extends beyond documentation to explore the second-order implications of these features on system latency, cost economics, and reliability, offering a roadmap for building the next generation of AI-native applications.5

## ---

**2\. The Gemini 3 Model Family: Engines of the Interaction Era**

To understand the utility of the Interactions API, one must first characterize the computational engines it orchestrates. The Gemini 3 architecture departs from the pure scaling laws of its predecessors, focusing instead on "reasoning density"—the ability to perform complex logic per token—and architectural specialization.5

### **2.1 Gemini 3 Pro: The Sparse Mixture-of-Experts Reasoning Engine**

Gemini 3 Pro stands as the flagship model, engineered specifically for high-fidelity instruction following, complex coding tasks, and autonomous agency. Architectural analysis suggests it utilizes a sparse Mixture-of-Experts (MoE) design, allowing it to activate only a subset of its massive parameter count for any given token generation. This architecture is crucial for the Interactions API because it supports the high-context throughput required for analyzing large datasets during stateful conversations without incurring the linear latency penalties associated with dense models.5

The defining characteristic of Gemini 3 Pro is its default "High" thinking level. Unlike Gemini 2.5, which required explicit prompting to engage in deep reasoning, Gemini 3 Pro natively employs a dynamic chain-of-thought process before emitting a final response. This internal monologue allows the model to self-correct and plan multi-step tool invocations, making it the primary engine for the Deep Research agent and complex stateful workflows.8 The implications for the developer are significant: the "Time to First Token" (TTFT) may be higher compared to non-reasoning models, but the "Time to Correct Answer" is drastically reduced for complex queries, as the model avoids the iterative prompting cycles often required to correct hallucinations in weaker models.10

### **2.2 Gemini 3 Flash: The Latency-Reasoning Hybrid**

Gemini 3 Flash redefines the category of "distilled" models. Historically, "Flash" or "Turbo" variants were quantized, stripped-down versions of larger models, trading capability for speed. Gemini 3 Flash breaks this dichotomy by incorporating the full reasoning architecture of the Pro series but exposing it through configurable "Thinking Levels".1

Benchmarks indicate that when fully engaged in "High" thinking mode, Gemini 3 Flash can achieve reasoning scores comparable to previous flagship models (e.g., scoring 90.4% on GPQA Diamond), yet it maintains the ability to operate at extremely low latencies for standard tasks.7 This versatility makes it the ideal candidate for the "Router" pattern in agentic architectures: a system can use Gemini 3 Flash in minimal thinking mode for initial intent classification and then dynamically escalate to high thinking for complex execution, all within the same model family and API surface.8

### **2.3 Model Versioning and Lifecycle Management**

Navigating the Google AI Studio ecosystem requires precise attention to model versioning. The Interactions API is tightly coupled with specific model snapshots that support its beta features.

Table 1: Gemini 3 Model Versions and Capabilities 5

| Model ID | Lifecycle Status | Primary Capability | Interaction API Support |
| :---- | :---- | :---- | :---- |
| gemini-3-pro | Active / Stable | High-reasoning, complex agency. | Full Native Support |
| gemini-3-flash | Active / Stable | Low-latency, configurable reasoning. | Full Native Support |
| gemini-3-pro-preview | Preview | Experimental features (e.g., Deep Research). | Required for Deep Research |
| gemini-3-flash-preview | Preview | Early access to new thinking configs. | Required for experimental levels |

The distinction between "Stable" and "Preview" is critical. The Deep Research agent, for instance, is currently accessible primarily through preview variants (e.g., deep-research-pro-preview), implying that production systems relying on this feature must be architected to handle potential breaking changes or schema updates associated with preview endpoints.12

## ---

**3\. The Interactions API Architecture: From Stateless to Persistent**

The core innovation covered in this report is the transition from the legacy v1beta/models/...:generateContent endpoint to the unified v1beta/interactions endpoint. This change represents a move from a stateless "Completion" paradigm to a persistent "Interaction" paradigm.2

### **3.1 The Limitations of Statelessness**

In the stateless architecture that defined the GPT-3 and Gemini 1.0 eras, every API call was an independent transaction. The "memory" of the conversation was an illusion maintained entirely by the client application, which had to re-transmit the full history of User and Model messages with every new prompt.

**Implications of Stateless Architectures:**

1. **Bandwidth Inflation:** As conversations grew, the payload size increased linearly, consuming bandwidth and increasing latency.  
2. **Context Drift:** Subtle inconsistencies in how clients serialized history (e.g., dropping tool outputs to save tokens) often led to the model losing track of its previous logic.  
3. **Security Risks:** Re-transmitting sensitive context over the wire repeatedly increased the surface area for interception.

### **3.2 The Interaction Object Schema**

The Interactions API introduces the Interaction object as a first-class citizen. When a client initiates a request, the server creates a persistent session state. The response from the API is not just a text string, but a complex object encapsulating the state of that session.2

Table 2: Comprehensive Analysis of the Interaction Resource Schema 2

| Field | Type | Description | Architectural Implication |
| :---- | :---- | :---- | :---- |
| id | String | A unique, opaque identifier for the interaction session (e.g., v1\_ChdPU0...). | This ID is the key to state persistence. It allows the client to reference the entire history in subsequent turns without re-uploading it. |
| status | Enum | Current state: in\_progress, completed, requires\_action, failed. | Fundamental for async workflows. requires\_action signals a halt for tool execution; in\_progress signals background processing (Deep Research). |
| previous\_interaction\_id | String | The ID of the immediately preceding interaction. | This links the current turn to the historical chain, enabling the server to reconstruct the context window automatically. |
| outputs | Array\[Content\] | The generated content, including text, tool calls, and thought summaries. | This is a polymorphic list. It may contain a functionCall object, a text part, or a thought object depending on the configuration. |
| background | Boolean | Flag to enable asynchronous server-side execution. | Essential for long-running agents. When true, the API returns immediately, and the client must poll for results. |
| store | Boolean | Whether to persist this interaction in Google's database. | Defaults to true to enable stateful features. Disabling this reverts the API to a quasi-stateless mode. |

### **3.3 Server-Side State Management via previous\_interaction\_id**

The previous\_interaction\_id parameter is the linchpin of this architecture. Instead of managing a local list of messages, the developer manages a linked list of Interaction IDs.

**The Stateful Workflow:**

1. **Turn 1:** Client sends input="Analyze this dataset...". API creates Interaction A.  
2. **Response:** API returns Interaction(id="A", output="Sure, I need to use code...").  
3. **Turn 2:** Client sends input="Proceed.", previous\_interaction\_id="A".  
4. **Processing:** Google's server looks up Interaction A, retrieves its full context (including hidden states and KV caches), and appends the new input.  
5. **Response:** API creates Interaction B (which points to A) and returns Interaction(id="B",...).13

This mechanism significantly reduces latency for long conversations because the server can reuse the Key-Value (KV) cache of the previous interaction. In a stateless model, the server must re-process the entire prompt history to rebuild the KV cache for every turn. By referencing previous\_interaction\_id, the model effectively "remembers" the pre-computed attention maps, leading to faster Time-to-First-Token (TTFT) and lower computational costs.3

## ---

**4\. Cognitive Configuration: Thinking Levels and Thought Summaries**

The Interactions API provides granular control over the "black box" of the model's reasoning. With Gemini 3, Google has deprecated the integer-based thinking\_budget of Gemini 2.5 in favor of semantic thinking\_level configurations. This shift reflects a move towards outcome-oriented configuration rather than resource-oriented micro-management.15

### **4.1 The Thinking Level Taxonomy**

The thinking\_config object, passed within the generation configuration, dictates the depth of the model's internal monologue. This is not merely a prompt engineering trick; it fundamentally alters the inference path within the model.8

Table 3: Detailed Configuration of Thinking Levels 8

| Level | Compatible Models | Behavior & Latency Profile | Optimal Use Case |
| :---- | :---- | :---- | :---- |
| minimal | Gemini 3 Flash | **Zero-Shot.** Disables internal chain-of-thought. Lowest latency (\<500ms). | Chatbots, simple classification, high-throughput formatting tasks where reasoning is unnecessary. |
| low | 3 Flash, 3 Pro | **Light Reasoning.** Performs a brief internal check before answering. Low latency. | Summarization, simple instruction following, extraction from clear text. |
| medium | Gemini 3 Flash | **Balanced.** A middle ground unique to Flash. Moderate latency. | General-purpose assistants, data extraction from complex documents, moderate logic puzzles. |
| high | 3 Flash, 3 Pro | **Deep Reasoning.** Extensive internal monologue, self-correction, and planning. High latency (2s+ TTFT). | **Default for 3 Pro.** Complex coding, math, multi-step agentic planning, rigorous constraint satisfaction. |

Implications for System Design:  
The availability of minimal and medium exclusively on Gemini 3 Flash allows for cost-optimization strategies. A system can default to gemini-3-flash with thinking\_level="minimal" for handling greeting and navigational queries at negligible cost. When the intent classifier detects a complex user request (e.g., "Debug this Python script"), the system can switch to gemini-3-pro with thinking\_level="high" within the same session context, leveraging the Interactions API to maintain the conversation history across model switches.9

### **4.2 Thought Summaries: Observability into the Black Box**

A persistent challenge with reasoning models is the opacity of their logic. The Interactions API addresses this with the include\_thoughts=True parameter. When enabled, the model does not just return the final answer; it returns a "Thought Summary"—a synthesized, human-readable distillation of its internal reasoning process.8

Mechanism:  
The raw, token-by-token chain of thought is often verbose and unstructured. The model processes this raw stream and generates a structured summary part in the response payload.  
**Schema Representation:**

JSON

{  
  "outputs":  
}

This feature is indispensable for debugging "Grey Box" agents. If a model fails to execute a tool correctly, the Thought Summary often reveals the logical error (e.g., "I assumed the user meant lead-acid batteries"), allowing the developer to refine the system instructions or prompt.8

## ---

**5\. Stateful Conversations and the Cryptography of Thought**

Perhaps the most critical technical constraint introduced in the Interactions API is the **Thought Signature**. This mechanism addresses the "Context Drift" vulnerability inherent in multi-turn tool use, where a model "forgets" the nuance of its original plan after the client returns a tool result.16

### **5.1 The Context Drift Problem**

In a standard interaction, the workflow for tool use is:

1. **Model:** "I need to search for the weather." (Internal State: *I am looking for rain probability to decide on an outfit recommendation.*)  
2. **API Output:** functionCall: get\_weather("London").  
3. **Client:** Executes tool, gets result "Rainy".  
4. **Client Request:** Sends functionResponse: "Rainy".  
5. **Model (Stateless):** Receives "Rainy". *Lost Context: Why did I ask for this? Oh, maybe just to report the weather.*  
6. **Final Output:** "It is rainy in London." (Misses the outfit recommendation).

### **5.2 The Thought Signature Solution**

Gemini 3 enforces continuity via **Thought Signatures**—opaque, encrypted strings that encapsulate the model's hidden state at the moment of the function call. This signature effectively "freezes" the model's reasoning process.15

The Enforcement Protocol:  
When Gemini 3 emits a functionCall, it always accompanies it with a thought\_signature. The Interactions API contract mandates that the client must return this signature exactly as received when submitting the tool result.  
**Technical Workflow for Manual Handling (Python/REST):**

1. Parsing the Call:  
   The client receives an interaction where outputs.functionCall is present. The client must also extract outputs.thought\_signature.  
2. Immutable Storage:  
   This string must be treated as a binary blob. It should not be modified, decoded, or truncated.  
3. Constructing the Response:  
   When sending the functionResponse, the request body must structurally mirror the call.  
   Python  
   \# Python Pseudocode for Interaction Response  
   client.interactions.create(  
       previous\_interaction\_id="prev\_id",  
       input\=  
           },  
           {  
               "role": "user",  
               "parts":  
           }  
       \]  
   )

Validation and Error Handling:  
Gemini 3 Pro enforces strict validation on these signatures. If a client attempts to send a functionResponse without the corresponding thought\_signature from the previous turn, the API will reject the request with a 400 Invalid Argument error. This "Strict Mode" ensures that the model never resumes execution from an ambiguous state, thereby significantly reducing hallucinations in complex, multi-step agentic workflows.16

## ---

**6\. The Deep Research Agent: Autonomous Long-Horizon Intelligence**

The **Deep Research Agent** represents the pinnacle of the Interactions API's capabilities. It is not merely a model configuration but a fully managed, server-side agentic loop powered by Gemini 3 Pro. It is designed for tasks that require tens or hundreds of steps—planning, searching, reading, synthesizing, and refining—which would be cost-prohibitive and architecturally complex to implement client-side.4

### **6.1 Architectural Distinction: Asynchronous Execution**

Standard LLM requests are synchronous: the client sends a prompt and holds the connection open until the response is generated. Deep Research tasks, however, can take minutes or even hours to complete comprehensively. Consequently, the Deep Research agent *requires* the use of the **Background Execution** pattern supported by the Interactions API.4

**The Asynchronous Lifecycle:**

1. Initiation (Fire and Forget):  
   The client sends a create request with agent="deep-research-pro-preview" and background=true.  
   * **Response:** The API immediately returns an Interaction object with status="in\_progress" and a valid id. The HTTP connection closes.  
2. Server-Side Orchestration:  
   On Google's infrastructure, the agent begins its loop:  
   * **Planning:** It decomposes the user's query (e.g., "Competitive landscape of solid-state batteries") into sub-topics.  
   * **Execution:** It executes parallel google\_search queries.  
   * **Ingestion:** It reads the content of the search results, utilizing Gemini 3 Pro's massive context window.  
   * **Synthesis:** It drafts sections of the report.  
   * **Recursion:** If data is missing, it updates its plan and executes new searches.18  
3. Polling (The Client Loop):  
   The client must periodically check the status of the task using the interactions.get method.

### **6.2 Implementation of the Polling Pattern**

Since the Interactions API avoids the complexities of webhooks in this beta phase, simple polling is the standard implementation pattern.

**Python Implementation Strategy (using google-genai):**

Python

import time  
from google import genai

\# strictly avoiding Vertex AI initialization  
client \= genai.Client(api\_key="YOUR\_AI\_STUDIO\_KEY") 

def run\_deep\_research(topic):  
    \# 1\. Start the Background Task  
    print(f"Initiating research on: {topic}")  
    interaction \= client.interactions.create(  
        agent="deep-research-pro-preview-12-2025",  
        input\=topic,  
        background=True  
    )  
      
    task\_id \= interaction.id  
    print(f"Task started. ID: {task\_id}")

    \# 2\. Polling Loop  
    while True:  
        \# Fetch the current state of the interaction  
        current\_state \= client.interactions.get(task\_id)  
          
        status \= current\_state.status  
        print(f"Current Status: {status}")  
          
        if status \== "completed":  
            \# The final report is in the last output part  
            report \= current\_state.outputs\[-1\].text  
            return report  
              
        elif status \== "failed":  
            raise Exception(f"Research failed: {current\_state.error}")  
              
        \# Wait before next poll to avoid rate limits  
        time.sleep(15) 

\# Example usage  
\# report \= run\_deep\_research("Impact of quantum computing on cryptography")

4

### **6.3 Steerability and Formatting Constraints**

A common misconception is that autonomous agents are "black boxes" that cannot be directed. The Deep Research agent supports **Steerability** via the initial prompt. The user can, and should, explicitly define the output structure.

**Effective Steering Prompts:**

* **Structure:** "Format the output as a strategic memo with an Executive Summary, three detailed technical sections, and a Risk Assessment conclusion."  
* **Tone:** "Adopt a skeptical, academic tone suitable for a PhD-level audience."  
* **Data:** "Include a Markdown table comparing the funding rounds of the top 5 startups identified."

The agent ingests these "meta-instructions" during its planning phase and uses them to constrain the final synthesis step, ensuring the report meets the user's formatting expectations despite the autonomy of the research process.4

## ---

**7\. Grounding and Tools: The Google Search Integration**

The Interactions API treats **Google Search** not just as a tool, but as a fundamental "Grounding" layer. In the Gemini 3 ecosystem, grounding is the mechanism by which the model anchors its creative generation in verifiable facts retrieved from the web.2

### **7.1 Configuring the Google Search Tool**

Unlike custom function calling, where the developer must define extensive JSON schemas for parameters, the google\_search tool is a built-in primitive. Enabling it is a matter of configuration in the tools list.

**JSON Configuration Schema:**

JSON

{  
  "tools": \[  
    {  
      "google\_search": {}   
    }  
  \]  
}

When this tool is present, the Interactions API activates the grounding engine. Gemini 3 Pro will automatically detect queries that require external knowledge (e.g., "What is the stock price of Google today?") and trigger the search tool.

### **7.2 Dynamic Retrieval: The Economics of Search**

A key innovation in Gemini 3 Flash is **Dynamic Retrieval**. Search is expensive—both in terms of latency (network hops) and cost (API credits). Dynamic Retrieval allows the model to assign a confidence score to its internal knowledge versus the query's temporal nature.

* **Static Queries:** "Who wrote Hamlet?" \-\> High internal confidence \-\> Search skipped \-\> Low Latency.  
* **Temporal Queries:** "Who won the Super Bowl in 2025?" \-\> Low internal confidence (temporal) \-\> Search triggered \-\> Higher Latency, High Accuracy.

This dynamic routing is handled entirely server-side by the Interactions API, providing an optimal balance between cost and correctness without developer intervention.19

### **7.3 Grounding Metadata and Verification**

For professional applications, simply getting an answer is insufficient; verification is required. When google\_search is used, the Interaction response includes **Grounding Metadata**.

**Structure of Grounding Metadata:**

* **Search Entry Point:** HTML snippets allowing the user to click through to the Google Search results page.  
* **Grounding Chunks:** Specific segments of the generated text are linked to specific web sources (URLs).

This metadata allows developers to render citations (e.g., "Gemini 3 Flash released in December 2025 ") in their UI, fostering trust and enabling users to verify the model's claims against primary sources.19

## ---

**8\. Implementation Strategy: Avoiding Vertex AI**

The mandate to strictly avoid Vertex AI requires vigilance during implementation. The Google Cloud ecosystem often conflates the two paths (AI Studio vs. Vertex AI), and default behaviors in SDKs can inadvertently trigger Vertex dependencies.

### **8.1 Authentication and Client Initialization**

The primary differentiator is the authentication mechanism. Vertex AI uses Google Cloud IAM (Service Accounts) and google.auth.default(). Google AI Studio uses simple API Keys.

**The Correct (AI Studio) Pattern:**

Python

import os  
from google import genai

\# Explicitly use API Key.   
\# Do NOT use project\_id or location, as these trigger Vertex paths.  
client \= genai.Client(api\_key=os.environ)

\# Correct Endpoint Verification  
\# The client should target generativelanguage.googleapis.com

**The Anti-Pattern (Vertex AI \- To Be Avoided):**

Python

\# AVOID THIS  
from google.cloud import aiplatform \# Vertex Library  
genai.init(project="my-project", location="us-central1") \# Vertex Config

Using the Vertex AI path would subject the application to different quota limits, pricing models, and potentially delayed access to Beta features like the Interactions API and Deep Research agent.21

### **8.2 Error Handling in Stateful Systems**

In a stateful Interaction architecture, error handling becomes more nuanced than in stateless systems.

* **Session Expiry:** Interaction IDs are not valid indefinitely. While the exact TTL (Time To Live) is subject to Beta policies, developers should handle 404 Not Found errors on interactions.get requests by initiating a new session (re-sending the context if necessary, though this degrades the benefits of the API).  
* **Validation Errors (400):** As discussed, 400 errors often indicate a Thought Signature mismatch. The recovery strategy here is not to retry the same request (which will fail again), but to rollback the client state to the last known valid interaction ID and restart the turn.16

## ---

**9\. Implications and Future Outlook**

The Interactions API is more than a new set of endpoints; it is a declaration that the future of AI is **Agentic**. By moving state management, reasoning configuration, and long-horizon execution to the server, Google is effectively creating an "Operating System for Agents."

**Second-Order Insights:**

1. **The Commoditization of RAG:** With tools like Deep Research and integrated Google Search, the need for developers to build custom retrieval pipelines (RAG) for general knowledge is diminishing. The value shifts to "Proprietary RAG"—grounding the model in private, enterprise data that Google cannot access.  
2. **Latency as a Variable, Not a Constant:** The introduction of Thinking Levels means that latency is no longer a fixed property of the model but a configurable runtime parameter. Applications can now be "Quality-Adaptive," spending more time (latency) on complex queries and less on simple ones, optimizing the user experience dynamically.  
3. **The Rise of the "Interaction ID" Economy:** As sessions become persistent, the Interaction ID becomes a valuable asset. It represents the "memory" of a user's engagement. Future iterations may allow these IDs to be shared, forked, or analyzed, creating new possibilities for collaborative AI experiences.

In conclusion, the Gemini Interactions API offers the requisite infrastructure for building the next generation of AI applications. By mastering the nuances of Gemini 3's thinking levels, enforcing state integrity with thought signatures, and leveraging the autonomous power of Deep Research, developers can transcend the limitations of chatbots and build true cognitive agents.

---

Data Sources:  
.1

#### **Works cited**

1. Google Gemini 3 Flash: release, technical profile, platform rollout, and more \- Data Studios, accessed December 19, 2025, [https://www.datastudios.org/post/google-gemini-3-flash-release-technical-profile-platform-rollout-and-more](https://www.datastudios.org/post/google-gemini-3-flash-release-technical-profile-platform-rollout-and-more)  
2. Interactions API \- Gemini API | Google AI for Developers, accessed December 19, 2025, [https://ai.google.dev/api/interactions-api](https://ai.google.dev/api/interactions-api)  
3. Interactions API: A unified foundation for models and agents \- Google Blog, accessed December 19, 2025, [https://blog.google/technology/developers/interactions-api/](https://blog.google/technology/developers/interactions-api/)  
4. Gemini Deep Research Agent | Gemini API | Google AI for Developers, accessed December 19, 2025, [https://ai.google.dev/gemini-api/docs/deep-research](https://ai.google.dev/gemini-api/docs/deep-research)  
5. Gemini (language model) \- Wikipedia, accessed December 19, 2025, [https://en.wikipedia.org/wiki/Gemini\_(language\_model)](https://en.wikipedia.org/wiki/Gemini_\(language_model\))  
6. Gemini 3 Flash: frontier intelligence built for speed \- Google Blog, accessed December 19, 2025, [https://blog.google/products/gemini/gemini-3-flash/](https://blog.google/products/gemini/gemini-3-flash/)  
7. Google Says Its New Gemini 3 Flash AI Model Is Better and Faster Than 2.5 Pro, accessed December 19, 2025, [https://www.cnet.com/tech/services-and-software/google-gemini-3-flash-release/](https://www.cnet.com/tech/services-and-software/google-gemini-3-flash-release/)  
8. Gemini thinking | Gemini API | Google AI for Developers, accessed December 19, 2025, [https://ai.google.dev/gemini-api/docs/thinking](https://ai.google.dev/gemini-api/docs/thinking)  
9. Get started with Gemini 3 | Generative AI on Vertex AI \- Google Cloud Documentation, accessed December 19, 2025, [https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/get-started-with-gemini-3](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/get-started-with-gemini-3)  
10. Intro to Gemini 3 Pro \- Colab \- Google, accessed December 19, 2025, [https://colab.research.google.com/github/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro\_gemini\_3\_pro.ipynb](https://colab.research.google.com/github/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_3_pro.ipynb)  
11. Model versions and lifecycle | Generative AI on Vertex AI \- Google Cloud Documentation, accessed December 19, 2025, [https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions)  
12. Release notes | Gemini API \- Google AI for Developers, accessed December 19, 2025, [https://ai.google.dev/gemini-api/docs/changelog](https://ai.google.dev/gemini-api/docs/changelog)  
13. Interactions API | Gemini API \- Google AI for Developers, accessed December 19, 2025, [https://ai.google.dev/gemini-api/docs/interactions](https://ai.google.dev/gemini-api/docs/interactions)  
14. Google Interactions API makes AI agents faster and more efficient \- Techzine Global, accessed December 19, 2025, [https://www.techzine.eu/news/analytics/137391/google-interactions-api-makes-ai-agents-faster-and-more-efficient/](https://www.techzine.eu/news/analytics/137391/google-interactions-api-makes-ai-agents-faster-and-more-efficient/)  
15. Migrating to Gemini 3: Implementing Stateful Reasoning with Thought Signatures \- Medium, accessed December 19, 2025, [https://medium.com/google-cloud/migrating-to-gemini-3-implementing-stateful-reasoning-with-thought-signatures-4f11b625a8c9](https://medium.com/google-cloud/migrating-to-gemini-3-implementing-stateful-reasoning-with-thought-signatures-4f11b625a8c9)  
16. Thought signatures | Generative AI on Vertex AI \- Google Cloud Documentation, accessed December 19, 2025, [https://docs.cloud.google.com/vertex-ai/generative-ai/docs/thought-signatures](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/thought-signatures)  
17. Google Opens Gemini Deep Research to Developers \- Unified AI Hub, accessed December 19, 2025, [https://www.unifiedaihub.com/ai-news/google-opens-gemini-deep-research-to-developers-game-changer-for-ai-powered-research-applications](https://www.unifiedaihub.com/ai-news/google-opens-gemini-deep-research-to-developers-game-changer-for-ai-powered-research-applications)  
18. Build with Gemini Deep Research \- Google Blog, accessed December 19, 2025, [https://blog.google/technology/developers/deep-research-agent-gemini-api/](https://blog.google/technology/developers/deep-research-agent-gemini-api/)  
19. Using Tools & Agents with Gemini API | Google AI for Developers, accessed December 19, 2025, [https://ai.google.dev/gemini-api/docs/tools](https://ai.google.dev/gemini-api/docs/tools)  
20. workshop-build-with-gemini/03-thinking-and-tools.ipynb at main \- GitHub, accessed December 19, 2025, [https://github.com/patrickloeber/workshop-build-with-gemini/blob/main/03-thinking-and-tools.ipynb](https://github.com/patrickloeber/workshop-build-with-gemini/blob/main/03-thinking-and-tools.ipynb)  
21. @google/genai \- The GitHub pages site for the googleapis organization., accessed December 19, 2025, [https://googleapis.github.io/js-genai/](https://googleapis.github.io/js-genai/)