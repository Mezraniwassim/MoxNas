# MoxNAS

MoxNAS is a specialized implementation for running TrueNAS Scale in an LXC container environment on Proxmox VE 8.4. It focuses on providing mount point-based storage solutions while maintaining core NAS functionality.

## Features

- LXC container management for TrueNAS Scale
- Mount point-based storage management
- Core NAS service support (SMB, NFS, FTP, iSCSI)
- Secure network service configuration
- Proxmox VE 8.4 integration

## Requirements

- Python 3.8+
- Proxmox VE 8.4
- LXC support
- Root privileges for container operations

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/moxnas.git
cd moxnas
```

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Basic usage example:

```python
from moxnas.core import ContainerManager
from moxnas.storage import StorageManager
from moxnas.network import NetworkManager
from moxnas.utils import setup_logging

# Set up logging
setup_logging(debug=True)

# Initialize container
container = ContainerManager("truenas-scale")

# Configure storage
storage = StorageManager(container.container_path)

# Set up network services
network = NetworkManager(container.container_path)
```

## Development

1. Install development dependencies:

```bash
pip install -r requirements.txt
```

1. Run tests:

```bash
pytest
```

1. Format code:

```bash
black .
```

## Security Considerations

- All mount operations require root privileges
- Network services are configured with secure defaults
- Password hashing and secure token generation included
- Path traversal protection implemented

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your chosen license]
