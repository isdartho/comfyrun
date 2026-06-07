from fastmcp import FastMCP
import logging
import json
import os
from run_workflow import run_workflow, save_image, DEFAULT_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
def generate_image(prompt: str) -> str:
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
        # Using defaults for server and port as per run_workflow.py's typical usage if not provided
        prompt_id, output_images = run_workflow(workflow, server="127.0.0.1", port=8188, config=DEFAULT_CONFIG)

        if not output_images:
            logger.warning("No images were returned from the workflow.")
            return "Error: No image data received from ComfyUI."

        # Save the first image from the first node that returned images
        node_id = list(output_images.keys())[0]
        images = output_images[node_id]

        # We only save the first image for this tool
        img_data = images[0]
        img_format = img_data['format']
        filename = f"output_{prompt_id}_{node_id}_0.{img_format}"

        save_image(img_data['data'], filename)

        full_path = os.path.abspath(os.path.join("output", filename))
        logger.info(f"Image saved to {full_path}")

        return f"Image successfully generated and saved to: {full_path}"

    except FileNotFoundError:
        logger.error(f"Workflow file not found: {workflow_path}")
        return f"Error: Workflow file {workflow_path} not found."
    except Exception as e:
        logger.exception(f"Unexpected error during image generation: {e}")
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
