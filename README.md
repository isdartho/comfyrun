# ComfyRun

ComfyRun is a lightweight Python utility designed to execute ComfyUI workflows via its API and capture output images directly through WebSockets.

## Features

- **Workflow Execution**: Run ComfyUI API-format JSON workflows from the command line.
- **Real-time Monitoring**: Tracks the execution progress of nodes via WebSocket.
- **Automatic Image Capture**: Automatically captures image data sent via `ETN_SendImageWebSocket` (or compatible nodes) and saves them to the local filesystem.
- **Dynamic Format Support**: Detects the image format (e.g., png, jpg) from the workflow node configuration, defaulting to PNG.
- **Configurable Connection**: Ability to specify the ComfyUI server address and port.

## Project Structure

- `run_workflow.py`: The main entry point of the application.
- `workflows/`: Directory to store your ComfyUI API JSON workflow files.
- `output/`: Directory where generated images are saved.
- `requirements.txt`: List of Python dependencies.

## Installation

### Prerequisites
- Python 3.x
- A running instance of ComfyUI with the API enabled.
- The `ETN_SendImageWebSocket` node from [comfyui-tooling-nodes](https://github.com/Acly/comfyui-tooling-nodes) (or a compatible custom node that sends binary image data over WebSockets).
  
  ![Example Workflow](workflows/example_workflow_zit.png)

### Setup
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd comfyrun
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Execute a workflow by providing the path to the API JSON file:

```bash
python run_workflow.py workflows/your_workflow.json
```

### Options

| Argument | Description | Default |
|----------|-------------|---------|
| `workflow_path` | Path to the ComfyUI API JSON file | Required |
| `--server` | ComfyUI server IP or hostname | `127.0.0.1` |
| `--port` | ComfyUI server port | `8188` |

### Example

To run a workflow on a remote server:
```bash
python run_workflow.py workflows/test_workflow.json --server 192.168.1.100 --port 8188
```

## Image Output

Images are saved in the `output/` folder using the following naming convention:
`output_{prompt_id}_{node_id}_{index}.{format}`

## License
Refer to the `LICENSE` file for licensing details.
