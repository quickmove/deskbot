#!/usr/bin/env python3
"""
WebSocket Server for DeskRobot
Receives audio from ESP32 and processes through VAD + ASR + LLM + TTS pipeline
"""

import asyncio
import websockets
import json
import os
import wave
import struct
import logging
from datetime import datetime
from typing import Optional

from server.config.settings import config
from server.core.pipeline import AudioPipeline, get_pipeline, PipelineConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global state
pipeline: Optional[AudioPipeline] = None
audio_buffer = bytearray()
buffer_lock = asyncio.Lock()
client_websocket = None


async def send_to_client(websocket, data: dict):
    """Send JSON message to client"""
    try:
        await websocket.send(json.dumps(data))
    except Exception as e:
        logger.error(f"Error sending to client: {e}")


async def send_audio_to_client(websocket, audio_data: bytes):
    """Send binary audio data to client"""
    try:
        # Send header with audio size
        header = struct.pack('!I', len(audio_data))
        await websocket.send(header + audio_data)
    except Exception as e:
        logger.error(f"Error sending audio to client: {e}")


async def handle_client(websocket):
    """Handle WebSocket client connection"""
    global client_websocket
    client_addr = websocket.remote_address
    client_websocket = websocket
    print(f"Client connected: {client_addr}")

    # Send welcome message
    await websocket.send(json.dumps({
        "type": "welcome",
        "message": "Connected to DeskRobot server",
        "timestamp": datetime.now().isoformat()
    }))

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                # Binary audio data
                async with buffer_lock:
                    audio_buffer.extend(message)

                # Process through pipeline
                if pipeline:
                    try:
                        result = await pipeline.process_audio(message)
                        if result and result.get("text"):
                            logger.info(f"Recognized: {result['text']}")

                            # Send recognition result to client
                            await websocket.send(json.dumps({
                                "type": "recognition",
                                "text": result["text"],
                                "timestamp": datetime.now().isoformat()
                            }))

                            # Send LLM response
                            if result.get("llm_response"):
                                logger.info(f"LLM Response: {result['llm_response']}")
                                await websocket.send(json.dumps({
                                    "type": "llm_response",
                                    "text": result["llm_response"],
                                    "timestamp": datetime.now().isoformat()
                                }))

                            # Send TTS audio
                            if result.get("tts_audio"):
                                logger.info(f"Sending TTS audio: {len(result['tts_audio'])} bytes")
                                await send_audio_to_client(websocket, result["tts_audio"])
                                await websocket.send(json.dumps({
                                    "type": "tts_complete",
                                    "timestamp": datetime.now().isoformat()
                                }))
                    except Exception as e:
                        logger.error(f"Pipeline error: {e}")

                # Log every 10KB received
                logger.debug(f"Received {len(message)} bytes audio data, total buffer: {len(audio_buffer)} bytes")
            else:
                # Text message
                try:
                    data = json.loads(message)
                    logger.info(f"Received command: {data}")

                    command = data.get("type")
                    if command == "save":
                        # Save audio to file
                        await save_audio()
                        await websocket.send(json.dumps({
                            "status": "saved",
                            "filename": get_latest_file()
                        }))

                    elif command == "status":
                        # Get pipeline status
                        status = {
                            "buffer_size": len(audio_buffer),
                            "pipeline_running": pipeline._running if pipeline else False
                        }
                        if pipeline:
                            vad_status = await pipeline.get_vad_status()
                            status.update(vad_status)
                            robot_state = pipeline.get_robot_state()
                            status.update(robot_state)

                        await websocket.send(json.dumps({
                            "type": "status",
                            "data": status
                        }))

                    elif command == "start":
                        # Start pipeline
                        if pipeline:
                            await pipeline.start()
                            await websocket.send(json.dumps({
                                "status": "started"
                            }))

                    elif command == "stop":
                        # Stop pipeline
                        if pipeline:
                            await pipeline.stop()
                            await websocket.send(json.dumps({
                                "status": "stopped"
                            }))

                    elif command == "clear":
                        # Clear buffer
                        async with buffer_lock:
                            audio_buffer.clear()
                        if pipeline:
                            await pipeline.clear_history()
                        await websocket.send(json.dumps({
                            "status": "cleared"
                        }))

                    elif command == "chat":
                        # Direct text chat (for testing)
                        if pipeline:
                            text = data.get("text", "")
                            if text:
                                response = await pipeline.chat(text)
                                await websocket.send(json.dumps({
                                    "type": "chat_response",
                                    "text": response,
                                    "timestamp": datetime.now().isoformat()
                                }))

                    elif command == "tts":
                        # Direct TTS synthesis (for testing)
                        if pipeline:
                            text = data.get("text", "")
                            if text:
                                tts_audio = await pipeline.tts.synthesize(text)
                                await send_audio_to_client(websocket, tts_audio)
                                await websocket.send(json.dumps({
                                    "type": "tts_complete",
                                    "timestamp": datetime.now().isoformat()
                                }))

                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON text: {message}")

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client disconnected: {client_addr}")
    finally:
        client_websocket = None
        # Save audio when client disconnects
        await save_audio()


async def save_audio():
    """Save audio buffer to WAV file"""
    if len(audio_buffer) == 0:
        logger.info("No audio data to save")
        return

    async with buffer_lock:
        filename = get_latest_file()
        filepath = config.audio_dir / filename

        with wave.open(str(filepath), 'wb') as wf:
            wf.setnchannels(config.audio.channels)
            wf.setsampwidth(config.audio.sample_width)
            wf.setframerate(config.audio.sample_rate)
            wf.writeframes(audio_buffer)

        logger.info(f"Saved {len(audio_buffer)} bytes to {filepath}")
        audio_buffer.clear()


def get_latest_file():
    """Generate filename with timestamp"""
    return f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"


async def main():
    """Main function"""
    global pipeline

    # Initialize pipeline with config
    pipeline = get_pipeline()
    await pipeline.start()

    # Setup callbacks
    async def on_recognized(text: str):
        logger.info(f"Pipeline recognized: {text}")

    async def on_llm_response(input_text: str, response: str):
        logger.info(f"LLM response: {response}")

    async def on_tts_ready(audio_data: bytes):
        logger.info(f"TTS audio ready: {len(audio_data)} bytes")
        if client_websocket:
            await send_audio_to_client(client_websocket, audio_data)

    pipeline.on_speechrecognized = on_recognized
    pipeline.on_llm_response = on_llm_response
    pipeline.on_tts_ready = on_tts_ready

    # Start server
    host = config.server.host
    port = config.server.port

    logger.info(f"Starting WebSocket server on {host}:{port}")
    logger.info(f"Audio will be saved to: {config.audio_dir}")
    logger.info(f"ASR model: {config.asr.model}, language: {config.asr.language}")
    logger.info(f"LLM provider: {config.llm.provider}, model: {config.llm.model}")
    logger.info(f"TTS model: {config.tts.model_name}")

    async with websockets.serve(handle_client, host, port):
        logger.info(f"Server running. Connect ESP32 to ws://<this-host>:{port}/")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nServer stopped")
