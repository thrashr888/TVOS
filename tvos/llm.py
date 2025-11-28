import os
from tvos.config import Config


class LLMClient:
    def __init__(self):
        self.provider = Config.LLM_PROVIDER
        # Prefer specific keys if provider is set, otherwise fallback to generic LLM_API_KEY
        if self.provider == "openai":
            self.api_key = Config.OPENAI_API_KEY or Config.LLM_API_KEY
        elif self.provider == "anthropic":
            self.api_key = Config.ANTHROPIC_API_KEY or Config.LLM_API_KEY
        elif self.provider == "gemini":
            self.api_key = Config.GEMINI_API_KEY or Config.LLM_API_KEY
        else:
            self.api_key = Config.LLM_API_KEY

        print(f"LLMClient initialized with provider: {self.provider}")

    def summarize(self, events):
        """
        Summarize a list of events into a topic string.
        """
        if not events:
            return "No events"

        # Format events for prompt
        text_samples = []
        for e in events[:10]:  # Take top 10
            payload = e.get("text_payload", "")
            source = e.get("source", "unknown")
            text_samples.append(f"[{source}] {payload}")

        prompt = f"""
        Analyze these log events and provide a concise 3-5 word topic summary that describes the main activity or theme.
        
        Events:
        {chr(10).join(text_samples)}
        
        Topic:
        """

        return self._call_llm(prompt, "topic")

    def explain_anomaly(self, event, neighbors):
        """
        Explain why an event is anomalous compared to its neighbors.
        """
        event_text = (
            f"[{event.get('source', 'unknown')}] {event.get('text_payload', '')}"
        )

        neighbor_texts = []
        for n in neighbors:
            neighbor_texts.append(f"- {n.get('text_payload', '')}")

        neighbor_block = (
            "\n".join(neighbor_texts)
            if neighbor_texts
            else "No similar historical events found."
        )

        prompt = f"""
        You are an expert system observability analyst. 
        Analyze the following ANOMALOUS EVENT compared to its NEAREST NEIGHBORS (normal events).
        Explain WHY this event is anomalous. Focus on semantic meaning, error codes, or intent shifts.
        
        ANOMALOUS EVENT:
        {event_text}
        
        NORMAL NEIGHBORS:
        {neighbor_block}
        
        Explanation (concise, 1-2 sentences):
        """

        return self._call_llm(prompt, "explanation")

    def _call_llm(self, prompt, task_type):
        try:
            if self.provider == "openai":
                return self._call_openai(prompt)
            elif self.provider == "anthropic":
                return self._call_anthropic(prompt)
            elif self.provider == "gemini":
                return self._call_gemini(prompt)
            else:
                return self._mock_response(task_type)
        except Exception as e:
            print(f"LLM Error ({self.provider}): {e}")
            return f"Error generating {task_type}"

    def _mock_response(self, task_type):
        if task_type == "topic":
            return "System Activity"
        else:
            return "This event deviates from the norm due to unusual keywords."

    def _call_openai(self, prompt):
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Fast, cheap
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )
        return response.choices[0].message.content.strip()

    def _call_anthropic(self, prompt):
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    def _call_gemini(self, prompt):
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
