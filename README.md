# Autonomous Customer Support Agent

> An AI agent that handles customer support tickets end-to-end  no human needed for routine issues, automatic escalation for anything sensitive.

---

## What does it do?

You submit a support ticket. The agent takes it from there:

1. **Reads the ticket** and figures out how urgent it is and what type of problem it is
2. **Looks up the customer** — their account, plan, billing status, and any orders
3. **Searches the knowledge base** for relevant articles and solutions
4. **Writes a response** tailored to the customer's specific situation
5. **Makes a decision:**
   - ✅ **Auto-resolve** — sends the solution immediately
   - ❓ **Clarify** — asks the customer for more info
   - 🚨 **Escalate** — pauses and waits for a human to review and approve
6. **Takes action** — updates the CRM and sends the email
7. **Logs everything** for a full audit trail

---

## Example flow

```
Customer: "I think my account was hacked"
         ↓
Agent classifies: urgency=CRITICAL, category=account
         ↓
Agent pulls account info: Enterprise plan, $14,400 lifetime value
         ↓
Agent finds KB article: "Account security and suspicious activity"
         ↓
Agent drafts response: step-by-step security lockdown instructions
         ↓
Agent decides: ESCALATE (security incident + high-value customer)
         ↓
⏸ PAUSED — human support agent reviews the draft
         ↓
Human approves → email sent + escalation ticket opened + CRM updated
```

---

## The 3 possible outcomes

| Outcome | When the agent uses it | Result |
|---|---|---|
| **Auto-resolve** | Clear answer exists, low or medium urgency | Sends solution email instantly |
| **Clarify** | Customer message is missing key info | Sends a follow-up question |
| **Escalate** | Security issue, critical urgency, or VIP customer | Waits for human sign-off before doing anything |

---

## Project structure

```
multi-agent ai system/
│
├── support_agent/
│   ├── state.py    → Defines the data that flows between every step
│   ├── tools.py    → Mock versions of CRM, order system, KB, and email
│   ├── nodes.py    → The 8 steps the agent runs through
│   ├── graph.py    → Connects the steps and handles branching logic
│   └── main.py     → 4 demo tickets you can run right now
│
├── .env            → Your API key goes here (never committed)
├── .env.example    → Template for the .env file
├── requirements.txt
└── README.md
```

---

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/GilPatrickDavis/SUPPORT-AGENT.git
cd SUPPORT-AGENT
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get a free API key

This project uses **Groq** for the AI — it's free, no credit card required.

1. Go to [console.groq.com](https://console.groq.com) and sign up
2. Click **API Keys → Create API key**
3. Copy the key (starts with `gsk_...`)

### 5. Add your key

```bash
cp .env.example .env
```

Open `.env` and paste your key:

```
GROQ_API_KEY=gsk_your_key_here
```

### 6. Run it

```bash
python -m support_agent.main
```

---

## What you'll see

The demo runs 4 tickets automatically and prints every step:

| # | Ticket | What the agent does |
|---|---|---|
| 1 | "I forgot my password" | Classifies as low urgency → sends reset instructions |
| 2 | "I was charged twice" | Finds order, checks refund policy → resolves or asks for more info |
| 3 | "My account was hacked" | Classifies as critical → **pauses for human approval** → then acts |
| 3b | Same hacked account ticket | Human **rejects** the draft → no email sent, just logged |

---

## How the human-in-the-loop works

For sensitive tickets, the agent doesn't act on its own. It stops, shows the human everything it found, and waits:

```
Agent runs → hits ESCALATE decision
          → graph PAUSES and saves its state
          → human sees: ticket summary, AI reasoning, draft email
          → human replies: approved ✓ or rejected ✗
          → graph RESUMES from exactly where it stopped
```

In a real product, the "human reply" would come from a Slack message, a web dashboard, or an email approval link. In this demo it's simulated in code.

---

## Tech stack

| Tool | Role |
|---|---|
| [LangGraph](https://github.com/langchain-ai/langgraph) | Orchestrates the agent steps and handles the pause/resume pattern |
| [Groq + Llama 3.3 70B](https://console.groq.com) | Free LLM that classifies tickets, drafts emails, and makes decisions |
| [LangChain](https://python.langchain.com) | Connects the LLM to the graph and handles structured outputs |

