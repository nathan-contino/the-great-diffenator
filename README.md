# Module sig-diff-vision 

A vision service that detects when images differ significantly from previous images. It compares each new image against a set of remembered images and returns detections when significant changes are found.

## Model natch:sig-diff-vision:sig-diff-vision

A vision service that detects significant changes between images by comparing them against a set of remembered images.

### Configuration

The following attribute template can be used to configure this model:

```json
{
"image_memories": <int>,
"required_diff": <float>,
"input_camera": <string>
}
```

#### Attributes

The following attributes are available for this model:

| Name          | Type   | Inclusion | Description                |
|---------------|--------|-----------|----------------------------|
| `image_memories` | int  | Required  | How many unique recent comparison images to retain for diffing. |
| `required_diff` | float | Optional  | A percentage, specified as a decimal between 0.0 and 1.0, that an input image must differ in a pixel diff from any image in the past N unique `image_memories` to be considered significantly different. |
| `input_camera` | string | Required | The camera whose images will be analyzed for significant changes. |

#### Example Configuration

The following configuration retains **5** unique recent images for diffing from a camera component named `camera-1`. If a new image differs from each comparison image by **at least 20%**:

- If this service has already retained 5 images:
  - Discards the oldest comparison image.
  - Adds the new image to the collection of comparison images.
- Returns a detection with class "significant_change" and confidence 1.0.

If the new image is more than 80% similar (in other words, less than 20% different) to a retained image, the service returns no detections.

```json
{
  "image_memories": 5,
  "required_diff": 0.2,
  "input_camera": "camera-1"
}
```

### DoCommand

This service provides functionality to clear the image memory using a DoCommand:

#### targeted_memory_erasure

Much like Lacuna, Inc, use this configuration to delete all stored comparison images:

```json
{
  "targeted_memory_erasure": {}
}
```

This command will:
1. Clear all stored image memories.
2. Return a success response.
3. Start the service fresh with the next image it receives.
