# Image Similarity Search API

## Project Description

This project provides an API to search for similar images from a database, and store them if needed. The API performs image similarity calculations based on feature extraction and allows users to upload and save images for future use.

### How to Run the Code
#### Prerequisites
- Python 3.11.x
- Python dependencies listed in `requirements.txt`

#### Steps to Run

0. **Download and Install Python**
  Download python 3.11 at http://python.org/ 

2. **Install dependencies**
   Install all required packages by running:

	```bash
	pip install -r requirements.txt
	```

3.  **Configure environment variables**
    Make sure the project has a `.env` file with the following variables:
    
    ```env
    IMAGES_DIR_PATH=path/to/images
    CACHE_DIR_PATH=path/to/images/cache
    ```
    
    These paths will be used to store processed images and their corresponding features.
    
4.  **Start the server**
    Run the FastAPI server with the following command:
    
    ```bash
    uvicorn server:app --reload
    ```
    
    The server will start on `http://127.0.0.1:8000` and begin accepting HTTP requests.
    
5.  **Use the API**
    You can now make HTTP requests to find similar images or save them to the server. See the available endpoints below.
    

### Available Endpoints

#### 1. Find Similar Images
-   **Endpoint**: `GET /image/find`
-   **Description**: Compares the image from a given URL with the database and returns similar images.
-   **Query Parameters**:
    
    -   `url`: The image URL to analyze.
        
    -   `max_results`: (Optional) Maximum number of results to return (default: 5).
        
    -   `max_similarity`: (Optional) Filter to exclude results below this similarity threshold.
        

**Example Request**:

```bash
curl "http://127.0.0.1:8000/image/find?url=https://example.com/image.jpg&max_results=3"
```

**Example Response**:

```json
{
  "request_id": "uuid",
  "results": [
    {
      "url": "http://127.0.0.1:8000/image/example1.jpeg",
      "similarity": 0.95
    }
  ]
}
```

#### 2. Save Image
-   **Endpoint**: `POST /image/save`
    
-   **Description**: Saves a new image to the server using the request ID returned from the `/image/find` endpoint.
    
-   **Request Body**:
```json
{
  "request_id": "uuid"
}
```

**Example Request**:
```bash
curl -X POST "http://127.0.0.1:8000/image/save" -H "Content-Type: application/json" -d '{"request_id": "uuid"}'
```

**Example Response**:
```json
{
  "message": "The image has been successfully saved and can be accessed at http://127.0.0.1:8000/image/file_name.jpg",
  "url": "http://127.0.0.1:8000/image/file_name.jpg"
}
```

### File Access
After saving, images can be accessed directly through their URL:
```
http://127.0.0.1:8000/image/file_name.jpg
```

Replace `file_name.jpg` with the actual file name returned in the save response.

### Background Tasks
The server automatically runs tasks to:

-   Clean up expired image requests every 60 seconds.
-   Refresh the database of stored images and features every 2 minutes.
    

These background tasks ensure the system stays clean and up to date with minimal manual intervention.

## License

This project is licensed under the MIT License - see the `LICENSE` file for more information.
