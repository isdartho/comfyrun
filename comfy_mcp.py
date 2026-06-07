from fastmcp import FastMCP
import logging
import json
import os
import base64
from dotenv import load_dotenv
from mcp.types import ImageContent
from run_workflow import run_workflow, DEFAULT_CONFIG

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Using server and port from environment variables
server = os.getenv("COMFY_SERVER", "127.0.0.1")
port = int(os.getenv("COMFY_PORT", "8188"))

# Create an MCP server
mcp = FastMCP("ComfyRun Server")

@mcp.tool()
def hello_mcp(name: str = "World") -> str:
    """
    A dummy function to verify the MCP server is working.

    Args:
        name: The name to greet.
    Returns:
        A friendly greeting.
    """
    logger.info(f"Hello MCP tool called with name: {name}")
    return f"Hello, {name}! The ComfyRun MCP server is online and working."

@mcp.tool()
def generate_image(prompt: str) -> ImageContent:
    """
    Generates an image using a pre-defined ComfyUI workflow and a given prompt.

    Args:
        prompt: The text prompt to use for image generation.
    Returns:
        The path to the saved image file.
    """
    logger.info(f"Generating image for prompt: {prompt}")

    workflow_path = "workflows/example_workflow_zit_t2i.json"
    try:
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)

        # Update node 6 input text field
        # We use string '6' because JSON keys are always strings
        if '6' in workflow:
            workflow['6']['inputs']['text'] = prompt
        else:
            logger.error(f"Node 6 not found in workflow {workflow_path}")
            return "Error: Node 6 not found in the example workflow."

        # Run workflow
        prompt_id, output_images = run_workflow(workflow, server=server, port=port, config=DEFAULT_CONFIG)

        if not output_images:
            logger.warning("No images were returned from the workflow.")
            return "Error: No image data received from ComfyUI."

        # Return the first image from the first node that returned images using ImageContent
        node_id = list(output_images.keys())[0]
        images = output_images[node_id]

        # Encode image data to base64 string
        img_bytes = images[0]['data']
        base64_image = base64.b64encode(img_bytes).decode('utf-8')
        img_format = images[0]['format']

        return ImageContent(
            type="image",
            data=base64_image,
            mimeType=f"image/{img_format.lower()}"
        )

    except FileNotFoundError:
        logger.error(f"Workflow file not found: {workflow_path}")
        return f"Error: Workflow file {workflow_path} not found."
    except Exception as e:
        logger.exception(f"Unexpected error during image generation: {e}")
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
