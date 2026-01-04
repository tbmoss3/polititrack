"""AI-powered bill summarization using OpenAI or Anthropic."""

from anthropic import Anthropic
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are a nonpartisan legislative analyst. Your task is to summarize bills in plain English for average voters.

Rules:
1. Write exactly 2 sentences
2. First sentence: What the bill does
3. Second sentence: Who it affects or why it matters
4. Use simple language (8th grade reading level)
5. Be completely neutral - no political commentary
6. Focus on facts, not opinions
7. Avoid jargon and acronyms

Example:
"This bill increases funding for public school lunch programs by $500 million annually. It would provide free meals to an additional 2 million low-income students across the country."
"""


class BillSummarizer:
    """AI-powered bill summarization service."""

    def __init__(self, provider: str = "openai"):
        """
        Initialize the summarizer.

        Args:
            provider: 'openai' or 'anthropic'
        """
        self.provider = provider

        if provider == "anthropic" and settings.anthropic_api_key:
            self.client = Anthropic(api_key=settings.anthropic_api_key)
        else:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.provider = "openai"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def summarize_bill(self, title: str, official_summary: str | None = None) -> str:
        """
        Generate a 2-sentence plain English summary of a bill.

        Args:
            title: The bill's official title
            official_summary: The official summary text (if available)

        Returns:
            2-sentence plain English summary
        """
        content = f"Bill Title: {title}"
        if official_summary:
            content += f"\n\nOfficial Summary:\n{official_summary[:2000]}"  # Limit to 2000 chars

        if self.provider == "anthropic":
            return await self._summarize_with_anthropic(content)
        else:
            return await self._summarize_with_openai(content)

    async def _summarize_with_openai(self, content: str) -> str:
        """Summarize using OpenAI API."""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Summarize this bill in exactly 2 sentences:\n\n{content}"},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    async def _summarize_with_anthropic(self, content: str) -> str:
        """Summarize using Anthropic API."""
        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Summarize this bill in exactly 2 sentences:\n\n{content}"},
            ],
        )
        return response.content[0].text.strip()

    async def batch_summarize(self, bills: list[dict]) -> dict[str, str]:
        """
        Summarize multiple bills.

        Args:
            bills: List of bill dictionaries with 'bill_id', 'title', and optionally 'summary_official'

        Returns:
            Dictionary mapping bill_id to AI summary
        """
        summaries = {}

        for bill in bills:
            bill_id = bill.get("bill_id")
            if not bill_id:
                continue

            try:
                summary = await self.summarize_bill(
                    title=bill.get("title", ""),
                    official_summary=bill.get("summary_official"),
                )
                summaries[bill_id] = summary
            except Exception as e:
                summaries[bill_id] = f"Summary unavailable: {str(e)}"

        return summaries


# Convenience function for one-off summarization
async def summarize_bill(title: str, official_summary: str | None = None, provider: str = "openai") -> str:
    """
    Quick function to summarize a single bill.

    Args:
        title: Bill title
        official_summary: Official summary text
        provider: 'openai' or 'anthropic'

    Returns:
        2-sentence summary
    """
    summarizer = BillSummarizer(provider=provider)
    return await summarizer.summarize_bill(title, official_summary)
