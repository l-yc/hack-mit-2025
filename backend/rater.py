import glob
import os
import re

from collections import defaultdict
from pathlib import Path
from pprint import pprint

import yaml

from prompter import prompt_claude_haiku_with_images
from templater import partial_render


def poll(agents: list[Path], files: list[str]) -> dict:
    print(f"Found {len(files)} image files")

    ratings = {}
    
    # Example usage with streaming
    for agent in agents:
        response = prompt_claude_haiku_with_images(
            partial_render(partial_render(
                open('./prompts/template.jinja').read(),
                {
                    'personality': open(agent).read()
                }
            ), context={"post_type": "Instagram Story for a fun philosophy club."}),
            image_paths=files,
            api_key=os.environ["CLAUDE_API_KEY"],
            max_tokens=4096,
            model="claude-3-haiku-20240307",
            stream=False  # Enable streaming
        )

        # Extract YAML from code blocks if present
        yaml_content = response
        if '```yaml' in response:
            # Extract content between ```yaml and ```
            match = re.search(r'```yaml\s*\n(.*?)\n```', response, re.DOTALL)
            if match:
                yaml_content = match.group(1)
        elif '```' in response:
            # Handle generic code blocks that might contain YAML
            match = re.search(r'```\s*\n(.*?)\n```', response, re.DOTALL)
            if match:
                yaml_content = match.group(1)
        ratings[agent] = defaultdict(lambda: 0, map=yaml.safe_load(yaml_content))

    return ratings


def select_photos(agents: list[Path], imgs:int = 2, img_dir: str="./demo/hack/") -> list[Path]:
    # Match common image extensions (case-insensitive if you normalize with .lower())
    image_extensions = ("*.jpg", "*.jpeg", "*.png", "*.heic", "*.gif", "*.bmp", "*.tiff", "*.webp")

    # Collect all images
    files = []
    for ext in image_extensions:
        files.extend(glob.glob(os.path.join(img_dir, ext)))
    
    ratings = poll(agents, files)

    score_per_file = sorted([
        (file, sum(ratings[agent][file] for agent in agents))
        for file in files
    ], key=lambda pair: pair[1], reverse=True)

    return [Path(file) for file, score in score_per_file[:imgs]]


if __name__ == "__main__":
    agents = [Path(agent) for agent in glob.glob('./prompts/agents/*.md')]
    pprint(select_photos(agents))