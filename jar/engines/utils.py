"""
Shared utility functions for query engines.
"""


def parse_llm_json_response(response_text: str) -> str:
    """
    Extract JSON from LLM response that may be wrapped in code blocks.
    
    Args:
        response_text: Raw text response from LLM
        
    Returns:
        Cleaned JSON string without code block markers
    """
    response_text = response_text.strip()
    if response_text.startswith("```json"):
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif response_text.startswith("```"):
        response_text = response_text.split("```")[1].split("```")[0].strip()
    return response_text
