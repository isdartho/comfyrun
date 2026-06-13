import websocket
import uuid
import json
import urllib.request
import urllib.parse
import argparse
import os
import logging
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default Configuration
DEFAULT_CONFIG = {
    "image_metadata_offset": 8, # Offset for binary image data from SaveImageWebsocket
    "image_node_class": "ETN_SendImageWebSocket", #Send Image (Websocket) class_type
    "default_image_format": "png",
}

client_id = str(uuid.uuid4())

def save_image(image_data, filename):
    """
    Saves image binary data to the output folder.
    """
    os.makedirs("output", exist_ok=True)
    with open(os.path.join("output", filename), "wb") as f:
        f.write(image_data)

def get_node(workflow, node_id):
    """
    Retrieves a node from the workflow by its ID.
    :param workflow: The workflow JSON dictionary.
    :param node_id: The ID of the node to retrieve.
    :return: The node's configuration or None if not found.
    """
    return workflow.get(node_id)

def queue_prompt(prompt, server_address):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.URLError as e:
        logger.error(f"Connection error while queueing prompt: {e}")
        raise

def get_history(prompt_id, server_address):
    try:
        with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}", timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.URLError as e:
        logger.error(f"Connection error while fetching history: {e}")
        raise

def run_workflow(workflow, server=None, port=None, config=None):
    """
    Runs a ComfyUI workflow.
    :param workflow: The workflow JSON dictionary.
    :param server: Server address (IP or hostname)
    :param port: Port number
    :param config: Configuration dictionary (optional)
    :return: A tuple of (prompt_id, output_images)
    :output_images: {node_id: [{format: JPEG/PNG, data:(binary)}...]}
    """
    if config is None:
        config = DEFAULT_CONFIG

    if server is None or port is None:
        raise ValueError("Server and port must be provided")
    server_address = f"{server}:{port}"

    logger.info("Queueing workflow...")
    try:
        prompt_id = queue_prompt(workflow, server_address)['prompt_id']
    except KeyError:
        logger.error("Server returned unexpected response format.")
        raise

    # Simple websocket listener to wait for completion
    ws = websocket.WebSocket()
    try:
        ws.connect(f"ws://{server_address}/ws?clientId={client_id}", timeout=30)

        logger.info("Waiting for workflow to complete...")
        current_node = None
        output_images = {}

        while True:
            try:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        data = message['data']
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            break # Execution finished

                        current_node_id = data['node']
                        current_node = get_node(workflow, current_node_id)
                        if current_node:
                            logger.info(f"Current Node[{current_node_id}]: {current_node.get('class_type')}")
                else:
                    # Binary frame — image data from SaveImageWebsocket
                    if current_node and current_node.get('class_type') == config['image_node_class']:
                        # Use the offset constant for better maintainability
                        images_output = output_images.get(current_node_id, [])
                        # Determine image format from the node configuration, defaulting to config['default_image_format']
                        img_format = current_node.get('inputs', {}).get('format', config['default_image_format'])
                        if isinstance(img_format, str):
                            img_format = img_format.lstrip('.')
                        else:
                            img_format = config['default_image_format']
                        images_output.append({ 'format':img_format, 'data':out[config['image_metadata_offset']:] })
                        output_images[current_node_id] = images_output
            except (websocket.WebSocketException, json.JSONDecodeError) as e:
                logger.error(f"WebSocket error during execution: {e}")
                break
    finally:
        ws.close()

    logger.info(f"Workflow {prompt_id} completed!")
    return prompt_id, output_images

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ComfyUI workflow API JSON")
    parser.add_argument("workflow_path", help="Path to the API format JSON file")
    parser.add_argument("--server", default="127.0.0.1", help="ComfyUI server address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8188, help="ComfyUI port (default: 8188)")

    args = parser.parse_args()

    # Override defaults with environment variables if set
    # Support both naming conventions for backward compatibility
    # Only override if using the argparse defaults (to allow explicit CLI args to take precedence)

    # Server address - check both COMFYUI_SERVER (legacy) and COMFY_SERVER (MCP)
    if args.server == "127.0.0.1":
        if "COMFYUI_SERVER" in os.environ:
            args.server = os.environ["COMFYUI_SERVER"]
        elif "COMFY_SERVER" in os.environ:
            args.server = os.environ["COMFY_SERVER"]

    # Port - check both COMFYUI_PORT (legacy) and COMFY_PORT (MCP)
    if args.port == 8188:
        port_env = None
        if "COMFYUI_PORT" in os.environ:
            port_env = os.environ["COMFYUI_PORT"]
        elif "COMFY_PORT" in os.environ:
            port_env = os.environ["COMFY_PORT"]

        if port_env is not None:
            try:
                args.port = int(port_env)
            except ValueError:
                logger.warning(f"Invalid port value: {port_env}, using default")

    try:
        # Load the workflow JSON file in the main execution block
        with open(args.workflow_path, 'r') as f:
            workflow = json.load(f)

        prompt_id, output_images = run_workflow(workflow, args.server, args.port, config=DEFAULT_CONFIG)
        if output_images:
            logger.info(f"Saving {len(output_images)} node(s) with images...")
            for node_id, images in output_images.items(): #For each node that has image
                for i, img_data in enumerate(images): #For each image of that node
                    img_format = img_data['format']
                    filename = f"output_{prompt_id}_{node_id}_{i}.{img_format}"
                    img_bytes = img_data['data']
                    save_image(img_bytes, filename)
                    logger.info(f"Saved: {filename}")
        else:
            logger.warning("No image data received!")

    except (json.JSONDecodeError, urllib.error.URLError, websocket.WebSocketException, FileNotFoundError) as e:
        logger.error(f"Task failed: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")