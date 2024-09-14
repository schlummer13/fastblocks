# FastBlocks for FastAPI

**FastBlocks** is a Python library specifically designed to integrate seamlessly with FastAPI, allowing you to efficiently store, retrieve, and delete images in WebP format. This library utilizes block-based storage, compression, encryption, and in-memory caching to manage image data efficiently, providing modern streaming responses for optimal performance.

## Features

- **WebP Conversion**: Automatically converts uploaded images to the WebP format for efficient storage and faster loading times.
- **Block-Based Storage**: Images are stored in blocks, optimizing disk usage and making retrieval fast and efficient.
- **Compression**: Optional compression of image data before storage to save disk space.
- **Encryption**: Optional encryption of image data using Fernet symmetric encryption for secure storage.
- **In-Memory Caching**: Frequently accessed image blocks are cached in memory for quick retrieval.
- **Streaming Response**: Delivers images as streaming responses, ensuring faster and more efficient data transfer.

## Installation

```bash
pip install fastblocks
```

## Usage with FastAPI

### 1. Setting Up the Block Manager

First, create an instance of the `BlockManager` class:

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastblocks import BlockManager
from io import BytesIO

app = FastAPI()

encryption_key = b'your-encryption-key-here'
manager = BlockManager(max_block_size=10*1024*1024, compression=True, encryption_key=encryption_key, cache_size=50)
```

### 2. Saving an Image

You can create an endpoint to save an image uploaded by the user. The image will be converted to WebP format and stored in the block storage:

```python
@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    image_data = await file.read()
    metadata = await manager.save_image(image_data)
    return {"message": "Image uploaded successfully", "metadata": metadata}
```

### 3. Loading an Image

Create an endpoint to retrieve a previously saved image by its block name, offset, and size. The image will be returned in WebP format as a streaming response:

```python
@app.get("/images/{block}/{offset}/{size}")
async def get_image(block: str, offset: int, size: int):
    try:
        image_data = await manager.read_image(block, offset, size)
        return StreamingResponse(BytesIO(image_data), media_type="image/webp")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")
```

### 4. Deleting an Image

Create an endpoint to delete an image from the block storage:

```python
@app.delete("/images/{block}/{offset}/{size}")
async def delete_image(block: str, offset: int, size: int):
    updated_metadata = await manager.delete_image(block, offset, size)
    return {"message": "Image deleted successfully", "updated_metadata": updated_metadata}
```

### 5. Running the FastAPI Application

Run your FastAPI application:

```bash
uvicorn main:app --reload
```

Now you can upload images, retrieve them as streaming responses, and delete them using the provided endpoints.

## Requirements

The following packages are required to use the FastBlockManager:

- `pillow`
- `cryptography`

## License

This project is licensed under the MIT License.
