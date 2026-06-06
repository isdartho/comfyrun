import websocket
import uuid
import json
import urllib.request
import urllib.parse
import argparse

server_address = None # Global variable to be set by arguments
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}") as response:
        return json.loads(response.read())


def run_workflow(workflow_path, inputs=None, server=None, port=None):
    """
    Runs a ComfyUI workflow from a JSON file.
    :param workflow_path: Path to the API format JSON file.
    :param inputs: Dictionary of node_id: {field: value} to override.
    :param server: Server address (IP or hostname)
    :param port: Port number
    """
    global server_address
    if server and port:
        server_address = f"{server}:{port}"

    with open(workflow_path, 'r') as f:
        workflow = json.load(f)

    if inputs:
        for node_id, overrides in inputs.items():
            if node_id in workflow:
                workflow[node_id].update(overrides)

    print(f"Queueing workflow from {workflow_path}...")
    prompt_id = queue_prompt(workflow)['prompt_id']

    # Simple websocket listener to wait for completion
    ws = websocket.WebSocket()
    ws.connect(f"ws://{server_address}/ws?clientId={client_id}")

    print("Waiting for workflow to complete...")
    current_node = ""
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break # Execution finished
                current_node = data['node']
                print(f"Current Node: {current_node}")
        else:
            # Binary frame — image data from SaveImageWebsocket
            if current_node == "ETN_SendImageWebSocket":
                images_output = output_images.get(current_node, [])
                # The first 8 bytes are type/meta, rest is image data
                images_output.append(out[8:])
                output_images[current_node] = images_output

    print(f"Workflow {prompt_id} completed!")
    print(f"Received {len(output_images)} image(s) via WebSocket.") if output_images else print("No image data received!")
    print(json.dumps(output_images))
    return prompt_id

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ComfyUI workflow API JSON")
    parser.add_argument("workflow_path", help="Path to the API format JSON file")
    parser.add_argument("--server", default="127.0.0.1", help="ComfyUI server address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8188, help="ComfyUI port (default: 8188)")
    parser.add_argument("--inputs", help="JSON string of input overrides (e.g. '{\"3\": {\"seed\": 123}}')")

    args = parser.parse_args()

    try:
        overrides = json.loads(args.inputs) if args.inputs else None
        run_workflow(args.workflow_path, overrides, args.server, args.port)
    except Exception as e:
        print(f"Error: {e}")
