# Originator Guide: Working with the Core Voice Agent

Welcome to the team! This guide explains how to effectively work with **Jason**, our autonomous AI Voice Agent, to maximize your pipeline efficiency.

## 🤖 Meet Jason (The AI Agent)
Jason is an autonomous mortgage specialist who handles the front-end of our 11-touch sales cadence. He qualifies leads, handles initial objections, and orchestrates follow-ups so you can focus on closing.

## 📥 How You Receive Leads (The Handoff)
Jason is programmed to transition "hot" leads to you once they are qualified. You will see these in Salesforce in two primary ways:

1.  **High-Priority Tasks**: When Jason books an appointment or identifies an urgent need, he creates a Salesforce Task assigned to you with the subject: `🔥 ACTION REQUIRED: Appointment Booked via AI`.
2.  **Call Logs**: Every interaction Jason has is logged as a closed task on the Lead record. You can review the **AI Thought Signature** and **Notes** to understand the client's current sentiment and goals.

## 📋 Managing Your "To-Dos"
*   **Review Notes**: Before calling a lead Jason has qualified, check the latest call logs. Jason records the client's loan program interest (VA, Conventional, Jumbo) and any specific concerns mentioned.
*   **Update Disposition**: Once you speak with a lead, update the Lead Status in Salesforce as usual. This informs Jason's cadence logic (e.g., if you haven't reached them, Jason may initiate a follow-up SMS or Email).

## 🚀 The 11-Touch Cadence
Jason persists across an 11-step follow-up series. 
*   **Automated Touches**: Jason will handle outbound calls, SMS, and emails during the early stages of the funnel.
*   **Your Role**: You enter the flow when a client requests a "Warm Handoff" or when they trigger a "Qualified" event.

## 🛡️ Compliance & Safety
*   **Rate Discussions**: Jason is restricted from quoting specific rates. He will always defer to you for official quotes.
*   **Disclosure**: Jason identifies as an AI in his opening statement to ensure transparency and compliance with telephony regulations.

## 💡 Best Practices
*   **Speed to Lead**: When you see a high-priority task from Jason, try to follow up within 60 minutes.
*   **Trust the Context**: Use the "AI Reason" provided in the task description to start your conversation. (e.g., *"I see you were just speaking with Jason about a VA streamline refinance..."*)

---
*Created for Phil Hills AI Lab | Feb 2026*
