# Vision Memory Agent

Vision Memory Agent is an intelligent visual memory system based on the RDK X3 development board. The system uses a camera to capture real-time images, performs object recognition and visual memory recording on the edge device, and provides an interactive web interface on the PC side.

This project aims to build a lightweight visual memory agent that can observe the environment, recognize objects, remember detected targets, and display memory records through a visual frontend interface. It combines edge AI perception, visual memory management, and human-computer interaction.

## Features

- Real-time camera video streaming
- Object detection and recognition
- Visual memory recording and updating
- Object appearance count statistics
- Memory status visualization
- Gesture interaction
- Web-based frontend interface
- Frontend and backend separated architecture
- Edge deployment based on RDK X3

## Project Structure

Vision-Memory-Agent/
├── backend/ Backend service running on RDK X3
├── frontend/ Web frontend running on PC
├── docs/ Project documents and related materials
├── README.md English project description
└── README_cn.md Chinese project description

## System Architecture

The project adopts a frontend-backend separated architecture.

The backend runs on the RDK X3 development board and is responsible for camera access, video stream output, object recognition, memory management, and API services.

The frontend runs in the PC browser and obtains real-time video streams, recognition results, and visual memory data from the backend through HTTP APIs.

## Technology Stack

Backend:

- Python 3
- FastAPI
- Uvicorn
- OpenCV
- RDK X3
- USB Camera

Frontend:

- React
- Vite
- JavaScript / JSX
- SCSS
- Three.js

## Main Modules

## 1. Video Stream Module

The system captures real-time images from the camera and provides video stream output through the backend API.

## 2. Object Recognition Module

The backend analyzes video frames and recognizes common objects in the scene, such as cups, phones, books, bottles, keyboards, mice, and people.

## 3. Visual Memory Module

The system records recognized objects, including object category, confidence, position, detection count, and recent status. It reduces repeated memory records for the same object in similar positions and maintains a lightweight visual memory list.

## 4. Gesture Interaction Module

The frontend supports gesture-based interaction, allowing users to interact with the visual memory system in a more natural way.

## 5. Visualization Interface

The frontend provides a visual dashboard including real-time video, memory records, status cards, and 3D-style interactive elements.

## Backend Startup

Enter the backend directory:

cd backend

Install dependencies:

pip3 install -r requirements.txt

Start the backend service:

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

After startup, the backend service will be available at:

http://<RDK_X3_IP>:8000

## Frontend Startup

Enter the frontend directory:

cd frontend

Install dependencies:

npm install

Start the frontend development server:

npm run dev

Then open the frontend address in the browser according to the terminal output.

## API Overview

Common backend APIs include:

GET /api/video/stream
GET /api/memory/status
POST /api/memory/reset
GET /api/status/current

The actual API paths should follow the backend implementation in this repository.

## Deployment Description

1. Connect the USB camera to the RDK X3 board.
2. Start the backend service on the RDK X3 board.
3. Start the frontend service on the PC.
4. Access the frontend page through the browser.
5. View real-time video, recognition results, and visual memory records.

## Project Highlights

- Uses RDK X3 as the edge AI computing platform.
- Combines object recognition with visual memory management.
- Provides a visual and interactive frontend interface.
- Supports real-time camera stream and memory status display.
- Separates frontend and backend for clearer engineering structure.
- Suitable for embedded AI application scenarios and intelligent human-computer interaction demonstrations.

## Application Scenarios

- Embedded AI demonstration
- Intelligent visual assistant
- Human-computer interaction experiment
- Edge vision perception system
- Smart classroom or smart desktop interaction
- Object memory and environment awareness applications

## Notes

- Please ensure that the camera is correctly connected before starting the backend.
- Please modify the backend service address in the frontend configuration according to the actual RDK X3 IP address.
- This project is mainly used for competition demonstration and embedded AI application verification.

## License

This project is used for learning, research, and competition demonstration.

------
