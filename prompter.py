from os import environ
from typing import Optional

import anthropic
from templater import partial_render

def prompt_claude_haiku(
    message: str, 
    api_key: Optional[str] = None,
    max_tokens: int = 200
) -> str:
    """
    Send a prompt to Claude Haiku and return the response.
    
    Args:
        message: The prompt/message to send to Claude
        api_key: Your Anthropic API key (if not set as environment variable)
        max_tokens: Maximum tokens in the response
        
    Returns:
        Claude's response as a string
    """
    
    # Initialize the client
    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
    else:
        # This will use the ANTHROPIC_API_KEY environment variable
        client = anthropic.Anthropic()
    
    try:
        # Send the message to Claude Haiku
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Claude Haiku model
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": message
                }
            ]
        )
        
        # Extract and return the text response
        return response.content[0].text
        
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    print(prompt_claude_haiku(partial_render(
        open('./prompts/template.jinja').read(),
        {
            'personality': open('./prompts/alex.md').read()
        }),
        api_key=environ["CLAUDE_API_KEY"],
        max_tokens=100
    ))