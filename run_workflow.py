import websocket
import uuid
import json
import urllib.request
import urllib.parse
import argparse
import os

# Configuration Constants
IMAGE_METADATA_OFFSET = 8 # Offset for binary image data from SaveImageWebsocket
IMAGE_NODE_CLASS = "ETN_SendImageWebSocket"
DEFAULT_IMAGE_FORMAT = "png"

server_address = None # Global variable to be set by arguments
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

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.URLError as e:
        print(f"Connection error while queueing prompt: {e}")
        raise

def get_history(prompt_id):
    try:
        with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}", timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.URLError as e:
        print(f"Connection error while fetching history: {e}")
        raise

def run_workflow(workflow, server=None, port=None):
    """
    Runs a ComfyUI workflow.
    :param workflow: The workflow JSON dictionary.
    :param server: Server address (IP or hostname)
    :param port: Port number
    :return: A tuple of (prompt_id, output_images)
    :output_images: {node_id: [{format: JPEG/PNG, data:(binary)}...]}
    """
    global server_address
    if server and port:
        server_address = f"{server}:{port}"

    print(f"Queueing workflow...")
    try:
        prompt_id = queue_prompt(workflow)['prompt_id']
    except KeyError:
        print("Server returned unexpected response format.")
        raise

    # Simple websocket listener to wait for completion
    ws = websocket.WebSocket()
    try:
        ws.connect(f"ws://{server_address}/ws?clientId={client_id}", timeout=30)

        print("Waiting for workflow to complete...")
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
                            print(f"Current Node: {current_node.get('class_type')}")
                else:
                    # Binary frame — image data from SaveImageWebsocket
                    if current_node and current_node.get('class_type') == IMAGE_NODE_CLASS:
                        # Use the offset constant for better maintainability
                        images_output = output_images.get(current_node_id, [])
                        # Determine image format from the node configuration, defaulting to DEFAULT_IMAGE_FORMAT
                        img_format = current_node.get('inputs', {}).get('format', DEFAULT_IMAGE_FORMAT)
                        if isinstance(img_format, str):
                            img_format = img_format.lstrip('.')
                        else:
                            img_format = DEFAULT_IMAGE_FORMAT
                        images_output.append({ 'format':img_format, 'data':out[IMAGE_METADATA_OFFSET:] })
                        output_images[current_node_id] = images_output
            except (websocket.WebSocketException, json.JSONDecodeError) as e:
                print(f"WebSocket error during execution: {e}")
                break
    finally:
        ws.close()

    print(f"Workflow {prompt_id} completed!")
    return prompt_id, output_images

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ComfyUI workflow API JSON")
    parser.add_argument("workflow_path", help="Path to the API format JSON file")
    parser.add_argument("--server", default="127.0.0.1", help="ComfyUI server address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8188, help="ComfyUI port (default: 8188)")

    args = parser.parse_args()

    try:
        # Load the workflow JSON file in the main execution block
        with open(args.workflow_path, 'r') as f:
            workflow = json.load(f)

        prompt_id, output_images = run_workflow(workflow, args.server, args.port)
        if output_images:
            print(f"Saving {len(output_images)} node(s) with images...")
            for node_id, images in output_images.items(): #For each node that has image
                for i, img_data in enumerate(images): #For each image of that node
                    img_format = img_data['format']
                    filename = f"output_{prompt_id}_{node_id}_{i}.{img_format}"
                    img_bytes = img_data['data']
                    save_image(img_bytes, filename)
                    print(f"Saved: {filename}")
        else:
            print("No image data received!")

    except (json.JSONDecodeError, urllib.error.URLError, websocket.WebSocketException, FileNotFoundError) as e:
        print(f"Task failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
