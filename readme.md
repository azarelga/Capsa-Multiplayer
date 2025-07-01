# Capsa Multiplayer Game
<img width="1045" alt="Screenshot 2025-06-29 at 22 00 35" src="https://github.com/user-attachments/assets/6e1b84a1-aa32-4457-8ee7-a38da723d2eb" />
 
Created by:
| Nama |NRP    | 
| :---:   | :---: | 
| Steven Gerard Lekatompessy Nathaniel | 5025221045  | 
| Azarel Grahandito Adi | 5025221126   | 
| Naufal Khairul Rizky | 5025221127  | 


A Big Two (Capsa Banting) card game implementation with multiple network protocols support including TCP and HTTP implementations, featuring both human players and AI opponents. This game is dedicated for our years in Senior High School where we spent most of our time sharing a core memory experience with our friends by playing this card game.

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Our House Rules](#our-house-rules)
- [Contributions](#contributions)

## Overview

This project implements a multiplayer Capsa (Big Two) card game with support for 1-4 players. The game features a modular architecture supporting multiplse network protocols (TCP and HTTP) with automatic AI player filling for incomplete sessions. The client includes a pygame-based graphical user interface.

## Project Structure

```
fp_progjar/
├── common/                 # Shared game logic and base classes
│   ├── game.py            # Core game mechanics, UI functions, and card logic
│   ├── server.py          # Base server classes and game state management
│   └── __init__.py        # Common module exports
├── tcp/                   # TCP implementation
│   ├── client.py          # TCP client with pygame UI
│   ├── server.py          # Basic TCP server
│   ├── server_redis.py    # Production TCP server with Redis
│   └── __init__.py        # TCP module exports
├── custom_http/           # HTTP implementation
│   ├── client.py          # HTTP client with requests library
│   ├── server.py          # HTTP server wrapper
│   ├── http_protocol.py   # Custom HTTP protocol and game API
│   └── __init__.py        # HTTP module exports
├── utils/                 # Utilities and testing
│   ├── test_redis_connection.py  # Redis connection testing
│   └── server.service     # Systemd service file
├── requirements.txt       # Python dependencies
├── reference.py          # HTTP server reference implementation
└── readme.md             # Project documentation
```

## Requirements

- Python 3.7+
- pygame
- pygame_cards
- requests
- redis (for production TCP server)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/azarelga/Capsa-Multiplayer
   cd capsa-multiplayer
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **For Redis support (optional):**
   - Set up Azure Cache for Redis or local Redis instance
   - Update Redis connection settings in `tcp/server_redis.py`

## Usage

### Running TCP Server

**Basic TCP Server:**
```bash
python -m tcp.server
```

**Production TCP Server with Redis:**
```bash
python -m tcp.server_redis
```

### Running HTTP Server

```bash
python -m custom_http.server
```

### Running Clients

**TCP Client:**
```bash
python -m tcp.client
```

**HTTP Client:**
```bash
python -m custom_http.client
```

### Game Flow

1. **Start Server**: Choose TCP or HTTP implementation
2. **Connect Clients**: Run client and connect to server
3. **Session Management**:
   - Create new session (becomes session creator)
   - Join existing session (browse available sessions)
4. **Game Play**:
   - Wait for players (2-4 required)
   - AI automatically fills empty slots (**Only work for TCP Implementation**)
   - Play cards using mouse selection
   - Pass turn when unable to play

## Our House Rules

Capsa (Big Two) is a card climbing game where:

1. **Objective**: Be the first to play all your cards
2. **Card Ranking**: 3 (lowest) to 2 (highest), suits: ♦ < ♣ < ♥ < ♠
3. **Valid Plays**:
   - Single cards
   - Pairs (two cards of same rank)
   - Three of a kind
   - Five-card hands (straight, flush, full house, etc.)
4. **Starting**: Player with 3♦ starts the game
5. **Turn Order**: Clockwise, must play higher cards or pass
6. **Round Reset**: When 3 consecutive players pass

## Architecture

### Core Components

- **`common/game.py`**: Game logic, card handling, pygame UI components
- **`common/server.py`**: Base server classes, session management, game state
- **Protocol Implementations**: TCP and HTTP server/client pairs
I
### Network Architecture

```
Client (pygame UI) ←→ Protocol Layer (TCP/HTTP) ←→ Game Server ←→ Redis (optional)
                                ↓
                        Session Management ←→ Game Logic
```

## Configuration

### TCP Server Settings

- **Port**: 55556 (configurable in `tcp/server.py`)
- **Max Clients**: 10 concurrent connections
- **Timeout**: 30 seconds with ping/pong keepalive

### HTTP Server Settings

- **Port**: 8886 (configurable in `custom_http/server.py`)
- **Threading**: Automatic threading for concurrent requests
- **Session Timeout**: Configurable per session

### Redis Configuration

Update `tcp/server_redis.py` with your Redis settings:

```python
REDIS_HOST = 'your-redis-host'
REDIS_PORT = 6380
REDIS_PASSWORD = 'your-redis-password'
```

## Contributions

1. Azarel Grahandito Adi: pygame, endpoint logic
2. Steven Gerard Lekatompessy: Deployment, HTTP architecture
3. Naufal Khairul Rizky: GameSessions attributes, client session requests
