import sys
from typing import (Any, ClassVar, Dict, Final, List, Mapping, Optional,
                    Sequence, Tuple)

from typing_extensions import Self
from viam.services.vision import Vision
from viam.media.video import NamedImage, ViamImage
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import Geometry, ResourceName, ResponseMetadata
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import ValueTypes
import numpy as np
from PIL import Image
import io
from viam.components.camera import Camera


class DiffVision(Vision):
    MODEL: ClassVar[Model] = Model(ModelFamily("natch", "the-great-diffenator"), "pixel-diff")

    def __init__(self, name: str):
        super().__init__(name)
        self.image_memories: List[np.ndarray] = []
        self.required_diff: float = 0.2  # Default 20% difference required
        self.input_camera: Optional[Camera] = None

    @classmethod
    def new_vision(cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        """Create a new instance of the DiffVision service.
        
        Args:
            config (ComponentConfig): The configuration for this resource
            dependencies (Mapping[ResourceName, ResourceBase]): The dependencies for this resource
            
        Returns:
            Self: The new DiffVision instance
        """
        service = cls(config.name)
        service.reconfigure(config, dependencies)
        return service

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> Dict[str, str]:
        """Validate the configuration for the diff vision service."""

        deps = []

        if "image_memories" not in config:
            raise ValueError("image_memories is required")
        if not isinstance(config["image_memories"], int) or config["image_memories"] < 1:
            raise ValueError("image_memories must be a positive integer")
            
        if "input_camera" not in config:
            raise ValueError("input_camera is required")
        if not isinstance(config["input_camera"], str):
            raise ValueError("input_camera must be a string")
        deps.append(config["input_camera"])
            
        if "required_diff" in config:
            if not isinstance(config["required_diff"], (int, float)):
                raise ValueError("required_diff must be a number")
            if not 0 <= config["required_diff"] <= 1:
                raise ValueError("required_diff must be between 0 and 1")
        
        # Return a mapping of dependency names to their types
        return deps

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        """This method allows you to dynamically update your service when it receives a new `config` object.

        Args:
            config (ComponentConfig): The new configuration
            dependencies (Mapping[ResourceName, ResourceBase]): Any dependencies (both implicit and explicit)
        """
        # Get the input camera from dependencies
        input_camera_name = config.attributes.fields["input_camera"].string_value
        input_camera_resource_name = ResourceName(
            namespace="rdk",
            type="component",
            subtype="camera",
            name=input_camera_name
        )
        
        if input_camera_resource_name not in dependencies:
            raise ValueError(f"Input camera {input_camera_name} not found in dependencies")
            
        # Cast the dependency to Camera type using the cast method
        self.input_camera = Camera.from_robot(dependencies[input_camera_resource_name])
        
        # Set configuration parameters
        self.image_memories = []  # Clear existing memories on reconfigure
        self.required_diff = config.attributes.fields["required_diff"].number_value if "required_diff" in config.attributes.fields else 0.2

    async def get_detections(self, image: ViamImage, extra: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get detections from the image if it differs enough from stored images."""
        if not self.input_camera:
            raise RuntimeError("Input camera not set")
            
        # Convert ViamImage to numpy array
        img = Image.open(io.BytesIO(image.data))
        img_array = np.array(img)
        
        # If no memories, store and return empty detections
        if not self.image_memories:
            self.image_memories.append(img_array)
            self.logger.info("No previous images to compare against, storing first image")
            return []
            
        # Check if image differs enough from all stored images
        is_different = True
        for i, memory in enumerate(self.image_memories):
            diff = self._calculate_image_diff(img_array, memory)
            self.logger.info(f"Image difference with memory {i}: {diff:.2%}")
            if diff < self.required_diff:
                is_different = False
                self.logger.info(f"Image too similar to memory {i} (diff: {diff:.2%} < required: {self.required_diff:.2%})")
                break
                
        if is_different:
            # Add new image to memories, removing oldest if at capacity
            if len(self.image_memories) >= self.image_memories:
                self.image_memories.pop(0)
                self.logger.info("Removed oldest image from memory")
            self.image_memories.append(img_array)
            self.logger.info(f"Image different enough from all memories, storing (diff > {self.required_diff:.2%})")
            return [{"confidence": 1.0, "class_name": "significant_change"}]
            
        # If not different enough, return empty list
        self.logger.info("Image not different enough from memories")
        return []

    async def get_classifications(self, image: ViamImage, count: int = 1, extra: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get classifications from the image if it differs enough from stored images."""
        detections = await self.get_detections(image, extra)
        return [{"class_name": d["class_name"], "confidence": d["confidence"]} for d in detections]

    async def get_object_point_clouds(self, camera_name: str, extra: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get object point clouds from the camera."""
        raise NotImplementedError("Point clouds not supported by diff vision service")

    async def do_command(self, command: Dict[str, ValueTypes], *, timeout: Optional[float] = None) -> Dict[str, ValueTypes]:
        """Handle custom commands."""
        if "targeted_memory_erasure" in command:
            self.image_memories = []
            return {"status": "success", "message": "All image memories cleared"}
        return {"status": "error", "message": "Unknown command"}

    def _calculate_image_diff(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Calculate the difference between two images as a percentage."""
        if img1.shape != img2.shape:
            # Resize the larger image to match the smaller one
            h1, w1 = img1.shape[:2]
            h2, w2 = img2.shape[:2]
            if h1 * w1 > h2 * w2:
                img1 = np.array(Image.fromarray(img1).resize((w2, h2)))
            else:
                img2 = np.array(Image.fromarray(img2).resize((w1, h1)))
        
        # Calculate mean absolute difference
        diff = np.mean(np.abs(img1.astype(float) - img2.astype(float)))
        max_diff = 255.0  # Maximum possible difference for uint8 images
        return diff / max_diff

    async def get_geometries(
        self, *, extra: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None
    ) -> List[Geometry]:
        self.logger.error("`get_geometries` is not implemented")
        raise NotImplementedError()

