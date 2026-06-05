"""AI service for interacting with Google Gemini API."""

import json
import logging
import time
from datetime import datetime
from typing import Generator

import requests
from flask import current_app

logger = logging.getLogger(__name__)


class AIService:
    """Handles all AI API interactions including streaming responses using raw HTTP requests to Gemini."""

    @staticmethod
    def _build_system_prompt(memory_context: str = "", document_context: str = "") -> str:
        """Build the system prompt with optional memory and document context."""
        current_date = datetime.now().strftime("%B %d, %Y")
        parts = [
            f"You are Smart AI Assistant, a helpful, accurate, and friendly AI assistant. "
            f"Today's date is {current_date}. "
            f"You provide clear, well-structured responses. Use markdown formatting when "
            f"appropriate. For code, always specify the language in code blocks."
        ]

        if memory_context:
            parts.append(
                f"\n\nUser context (remembered information):\n{memory_context}"
            )

        if document_context:
            parts.append(
                f"\n\nRelevant document context (use this to answer the user's question):\n"
                f"{document_context}\n\n"
                "When referencing information from documents, mention the source."
            )

        return "\n".join(parts)

    @staticmethod
    def _format_messages_for_gemini(messages: list[dict], max_messages: int = 20) -> list[dict]:
        """Convert OpenAI-style messages to Gemini contents format."""
        # Truncate context
        other_msgs = [m for m in messages if m["role"] != "system"]
        if len(other_msgs) > max_messages:
            other_msgs = other_msgs[-max_messages:]

        contents = []
        for msg in other_msgs:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        # Ensure alternating user/model turns (Gemini strict requirement)
        # If there are consecutive messages from the same role, combine them.
        merged_contents = []
        for content in contents:
            if merged_contents and merged_contents[-1]["role"] == content["role"]:
                merged_contents[-1]["parts"][0]["text"] += "\n\n" + content["parts"][0]["text"]
            else:
                merged_contents.append(content)

        # Gemini requires the first message to be from 'user'
        if merged_contents and merged_contents[0]["role"] != "user":
            merged_contents.pop(0)

        return merged_contents

    @classmethod
    def generate_response(
        cls,
        messages: list[dict],
        memory_context: str = "",
        document_context: str = "",
        model: str | None = None,
    ) -> dict:
        """Generate a non-streaming response from Gemini."""
        model = model or current_app.config["GEMINI_MODEL"]
        api_key = current_app.config["GEMINI_API_KEY"]
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        system_prompt = cls._build_system_prompt(memory_context, document_context)
        contents = cls._format_messages_for_gemini(messages)

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": contents,
            "tools": [{"googleSearch": {}}],
            "generationConfig": {
                "maxOutputTokens": current_app.config["GEMINI_MAX_TOKENS"],
                "temperature": current_app.config["GEMINI_TEMPERATURE"],
            }
        }

        try:
            start = time.time()
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            elapsed = time.time() - start

            content = ""
            if "candidates" in data and len(data["candidates"]) > 0:
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                
            tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)

            logger.info(
                "Gemini response generated in %.2fs | tokens=%d | model=%s",
                elapsed, tokens, model,
            )

            return {
                "content": content,
                "tokens_used": tokens,
                "model": model,
            }

        except requests.exceptions.RequestException as e:
            logger.error("Gemini API error: %s", e)
            return {"content": f"[Error] API Error: {str(e)}", "tokens_used": 0, "model": model}
        except Exception as e:
            logger.exception("Unexpected AI service error")
            return {"content": f"[Error] An unexpected error occurred: {str(e)}", "tokens_used": 0, "model": model}

    @classmethod
    def stream_response(
        cls,
        messages: list[dict],
        memory_context: str = "",
        document_context: str = "",
        model: str | None = None,
    ) -> Generator[str, None, None]:
        """Generate a streaming response via SSE from Gemini."""
        model = model or current_app.config["GEMINI_MODEL"]
        api_key = current_app.config["GEMINI_API_KEY"]
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"

        system_prompt = cls._build_system_prompt(memory_context, document_context)
        contents = cls._format_messages_for_gemini(messages)

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": contents,
            "tools": [{"googleSearch": {}}],
            "generationConfig": {
                "maxOutputTokens": current_app.config["GEMINI_MAX_TOKENS"],
                "temperature": current_app.config["GEMINI_TEMPERATURE"],
            }
        }

        try:
            with requests.post(url, headers={"Content-Type": "application/json"}, json=payload, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8').strip()
                        if decoded_line.startswith("data: "):
                            data_str = decoded_line[6:]
                            
                            try:
                                data = json.loads(data_str)
                                if "candidates" in data and len(data["candidates"]) > 0:
                                    parts = data["candidates"][0].get("content", {}).get("parts", [])
                                    for part in parts:
                                        if "text" in part:
                                            token = part["text"]
                                            yield f"data: {json.dumps({'token': token})}\n\n"
                            except json.JSONDecodeError:
                                pass

        except requests.exceptions.RequestException as e:
            logger.error("Gemini API stream error: %s", e)
            yield f"data: {json.dumps({'token': f'[Error] API Error: {str(e)}'})}\n\n"
        except Exception as e:
            logger.exception("Unexpected AI service stream error")
            yield f"data: {json.dumps({'token': f'[Error] An unexpected error occurred: {str(e)}'})}\n\n"

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimation (1 token ≈ 4 chars for English)."""
        return max(1, len(text) // 4)
