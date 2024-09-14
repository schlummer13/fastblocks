import os
import threading
import zlib
import asyncio
from collections import OrderedDict
from cryptography.fernet import Fernet
from PIL import Image
from io import BytesIO

class BlockManager:
    def __init__(self, block_dir='blocks', max_block_size:int=10*1024*1024, compression:bool=False, encryption_key:bytes|None=None, cache_size:int=5):
        self.block_dir:str = block_dir
        self.max_block_size:int = max_block_size
        self.compression:bool = compression
        self.encryption:bytes|None = encryption_key
        self.cipher: Fernet|None = Fernet(encryption_key) if encryption_key else None
        self.lock = threading.RLock()  # Use RLock for reentrant locking
        self.cache:OrderedDict = OrderedDict()  # LRU Cache for blocks
        self.cache_size:int = cache_size

        # Ensure the block directory exists
        if not os.path.exists(self.block_dir):
            os.makedirs(self.block_dir)

    def _compress_data(self, data:bytes) -> bytes:
        """Compress the data if compression is enabled."""
        if self.compression:
            return zlib.compress(data)
        return data

    def _decompress_data(self, data:bytes) -> bytes:
        """Decompress the data if compression is enabled."""
        if self.compression:
            return zlib.decompress(data)
        return data

    def _encrypt_data(self, data:bytes) -> bytes:
        """Encrypt the data if encryption is enabled."""
        if self.encryption and self.cipher:
            return self.cipher.encrypt(data)
        return data

    def _decrypt_data(self, data:bytes) -> bytes:
        """Decrypt the data if encryption is enabled."""
        if self.encryption and self.cipher:
            return self.cipher.decrypt(data)
        return data

    def _cache_block(self, block_path:str) -> None:
        """Cache the block data if not already in cache."""
        with self.lock:
            if block_path in self.cache:
                # Move the accessed block to the end of the cache (LRU policy)
                self.cache.move_to_end(block_path)
            else:
                # Read block data and store in memory
                with open(block_path, 'rb') as block_file:
                    block_data = block_file.read()
                    self.cache[block_path] = block_data

                # Maintain cache size, remove oldest if necessary
                if len(self.cache) > self.cache_size:
                    self.cache.popitem(last=False)

    def _convert_to_webp(self, image_data:bytes) -> bytes:
        """Convert image data to WebP format."""
        image = Image.open(BytesIO(image_data))
        output = BytesIO()
        image.save(output, format="WEBP")
        return output.getvalue()

    async def save_image(self, image_data:bytes) -> dict:
        """Convert image to WebP, save the image data to the current block, and return metadata."""
        
        if isinstance(image_data, bytes) == False:
            raise ValueError("image_data is not typ 'bytes'.")
        try:
            webp_data = self._convert_to_webp(image_data)
            async with asyncio.Lock():  # Ensuring that only one async operation writes at a time
                block_path = self._get_current_block_path()
                offset = 0

                if os.path.exists(block_path):
                    offset = os.path.getsize(block_path)
                else:
                    raise Exception("Block not found, during runtime.")
                compressed_data = self._compress_data(webp_data)
                encrypted_data = self._encrypt_data(compressed_data)

                # Synchronously open the file and write asynchronously
                with open(block_path, 'ab') as block_file:
                    await asyncio.to_thread(block_file.write, encrypted_data)

                return {
                    "block": os.path.basename(block_path),
                    "offset": offset,
                    "size": len(encrypted_data)
                }
        except Exception as e:
            raise RuntimeError(str(e))

    async def read_image(self, block:str, offset:int, size:int) -> bytes:
        """Read the image data from the specified block using the offset and size."""
        
        if not isinstance(block, str) or not isinstance(offset, int) or not isinstance(size, int):
            raise ValueError("Ungültige Eingabeparameter für 'block', 'offset' oder 'size'.")
        
        block_path = os.path.join(self.block_dir, block)

        if not os.path.exists(block_path):
            raise FileNotFoundError(f"Block file {block} does not exist.")

        try:
            # Cache block if not already cached
            self._cache_block(block_path)

            with self.lock:
                block_data = self.cache[block_path]

            image_data = block_data[offset:offset + size]
            decrypted_data = self._decrypt_data(image_data)
            decompressed_data = self._decompress_data(decrypted_data)

            return decompressed_data
        
        except Exception as e:
            raise RuntimeError(str(e))

    async def delete_image(self, block:str, offset:int, size:int) -> None:
        """Delete the image from the block and allow further writes to this block."""
        if not isinstance(block, str) or not isinstance(offset, int) or not isinstance(size, int):
            raise ValueError("Ungültige Eingabeparameter für 'block', 'offset' oder 'size'.")
        
        block_path = os.path.join(self.block_dir, block)

        if not os.path.exists(block_path):
            raise FileNotFoundError(f"Block file {block} does not exist.")

        try:
            async with asyncio.Lock():  # Ensuring that only one async operation modifies the block at a time
                # Load the entire block into memory
                with open(block_path, 'rb') as block_file:
                    block_data = block_file.read()

                # Remove the image data by slicing it out
                new_block_data = block_data[:offset] + block_data[offset + size:]

                # Synchronously open the file and write asynchronously
                with open(block_path, 'wb') as block_file:
                    await asyncio.to_thread(block_file.write, new_block_data)

                # Adjust the block path to continue writing in this block
                # If the block still has space left, it can continue to be written to
                new_offset = len(new_block_data)
        except Exception as e:
            raise RuntimeError(str(e))

    def _adjust_block_size(self, new_size:int) -> None:
        """Dynamically adjust the block size."""
        with self.lock:
            self.max_block_size = new_size

    def _get_current_block_path(self) -> str:
        """Find the current block file or create a new one if needed."""
        block_files = sorted([f for f in os.listdir(self.block_dir) if f.startswith('block_')])

        if block_files:
            current_block = block_files[-1]
        else:
            current_block = 'block_1.bin'

        current_block_path = os.path.join(self.block_dir, current_block)

        # Check if the current block is full
        if os.path.exists(current_block_path) and os.path.getsize(current_block_path) >= self.max_block_size:
            block_number = int(current_block.split('_')[1].split('.')[0]) + 1
            current_block = f'block_{block_number}.bin'
            current_block_path = os.path.join(self.block_dir, current_block)

        if not os.path.exists(current_block_path):
            open(current_block_path, 'wb').close()

        return current_block_path

    @staticmethod
    def generate_encryption_key() -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()

    
if __name__ == "__main__":
    encryption_key = b'w8GAZrfJeFqii2t8B0Mj36JvSWDIKM8YE2UkPeHfhdA='
    # Create an Manager with Block
    manager = BlockManager(max_block_size=10*1024*1024, compression=True, encryption_key=encryption_key, cache_size=50)

    # Example
    with open("bild.jpeg", "rb") as img_file:
        image_data = img_file.read()

    
    # Meta Data
    metadata = asyncio.run(manager.save_image(image_data))
    print(f"Image saved with metadata: {metadata}")

    bild = asyncio.run(manager.read_image(metadata['block'], metadata['offset'], metadata['size']))
    # delete image
