# backend/endpoints/blueprints/client_management/client_endpoints.py
"""
Client Registration and Polling Endpoints
Core client-facing endpoints for registration and status polling
Complete file with all functions and fixes for stream URL assignment
"""

import os
import time
import uuid
import logging
import traceback
import functools
from typing import Dict, Any, List, Optional
from flask import request, jsonify, current_app
import requests

logger = logging.getLogger(__name__)

# =====================================
# LOGGING DECORATOR
# =====================================

def log_function_call(func):
    """Decorator to log function calls with detailed information"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.info(f" {func_name} called with args={args}, kwargs={kwargs}")
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            logger.info(f" {func_name} completed successfully in {execution_time:.1f}ms")
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f" {func_name} failed after {execution_time:.1f}ms with error: {e}")
            logger.error(f" Error type: {type(e).__name__}")
            logger.error(f" Full traceback:\n{traceback.format_exc()}")
            
            # Log system state for debugging
            try:
                import psutil
                logger.error(f" System state at error in {func_name}:")
                logger.error(f"   CPU: {psutil.cpu_percent(interval=1):.1f}%")
                logger.error(f"   Memory: {psutil.virtual_memory().percent:.1f}%")
                logger.error(f"   Disk: {psutil.disk_usage('/').percent:.1f}%")
                logger.error(f"   Active processes: {len(psutil.pids())}")
            except Exception as sys_e:
                logger.error(f"Could not get system state: {sys_e}")
            
            raise
    return wrapper

# =====================================
# HELPER FUNCTIONS
# =====================================

def get_state():
    """Get the application state from Flask app config"""
    try:
        # Try to get from Flask app config
        state = current_app.config.get('APP_STATE')
        if state is not None:
            return state
        
        # Fallback: create a simple state object
        logger.warning("APP_STATE not found in config, using fallback state")
        return SimpleClientState()
        
    except Exception as e:
        logger.warning(f"Error getting state from Flask config: {e}, using fallback")
        return SimpleClientState()

class SimpleClientState:
    """Simple fallback client state for when APP_STATE is not available"""
    
    def __init__(self):
        self.clients = {}
        self.clients_lock = None  # No threading for now
    
    def get_client(self, client_id: str):
        """Get client by ID"""
        return self.clients.get(client_id)
    
    def get_all_clients(self):
        """Get all clients"""
        return self.clients
    
    def add_client(self, client_id: str, client_data: Dict):
        """Add or update client"""
        self.clients[client_id] = client_data
    
    def remove_client(self, client_id: str):
        """Remove client"""
        if client_id in self.clients:
            del self.clients[client_id]

def get_group_from_docker(group_id: str) -> Optional[Dict[str, Any]]:
    """
    Get group information from Docker discovery
    Clean import strategy - imports only when needed
    """
    try:
        from ..docker_management import get_all_groups
        groups = get_all_groups()
        
        # Search through the list to find the matching group
        for group in groups:
            if group.get("id") == group_id:
                return group
        
        # Group not found
        logger.warning(f"Group {group_id} not found in Docker discovery")
        return {}
        
    except ImportError:
        logger.warning("Docker management not available")
        return {}
    except Exception as e:
        logger.error(f"Error getting group from Docker: {e}")
        return {}

def update_client_assignments_after_restart(group_id: str, group_name: str):
    """Update all client assignments for a group after streaming restart"""
    try:
        logger.info(f"🔄 UPDATING CLIENT ASSIGNMENTS AFTER RESTART for group {group_name}")
        
        # Wait a bit for FFmpeg to fully start and be visible in process list
        import time
        time.sleep(3)  # Give FFmpeg time to start
        
        # Get all clients assigned to this group
        group_clients = []
        if hasattr(state, 'clients'):
            for client_id, client in state.clients.items():
                if client.get("group_id") == group_id:
                    group_clients.append((client_id, client))
        
        if not group_clients:
            logger.info(f"No clients found for group {group_name}")
            return
        
        logger.info(f"Found {len(group_clients)} clients assigned to group {group_name}")
        
        # Get stream IDs from database instead of extracting from FFmpeg
        from db.mongo import get_group_stream_ids
        db_stream_ids = get_group_stream_ids(group_id)
        
        if not db_stream_ids:
            logger.error(f"No database stream IDs found for group {group_name}")
            logger.error(f"This means streaming may not be active or database is not accessible")
            return
        
        logger.info(f"Found database stream IDs: {db_stream_ids}")
        
        # Update each client's stream assignment
        for client_id, client in group_clients:
            try:
                assignment_status = client.get("assignment_status")
                screen_number = client.get("screen_number")
                stream_assignment = client.get("stream_assignment")
                
                logger.info(f"Updating client {client_id}: status={assignment_status}, screen={screen_number}, stream={stream_assignment}")
                
                # Check if client already has a valid stream ID (not screen0...)
                existing_stream_id = client.get("stream_id")
                if existing_stream_id and not existing_stream_id.startswith("screen"):
                    logger.info(f"  Client {client_id} already has valid stream ID ({existing_stream_id}), skipping update")
                    continue
                
                # Determine the correct stream ID based on assignment type
                if assignment_status == "screen_assigned" and screen_number is not None:
                    # Screen assignment - use screen-specific stream ID from database
                    stream_key = f"test{screen_number}"
                    actual_stream_id = db_stream_ids.get(stream_key)
                    
                    if actual_stream_id:
                        logger.info(f"  Screen {screen_number} -> Stream ID: {actual_stream_id}")
                    else:
                        # Try to construct from base stream ID
                        base_stream_id = db_stream_ids.get("base")
                        if base_stream_id:
                            actual_stream_id = f"{base_stream_id}_{screen_number}"
                            logger.info(f"  Constructed: Screen {screen_number} -> Stream ID: {actual_stream_id}")
                        else:
                            logger.error(f"  No database stream ID found for screen {screen_number}, skipping client")
                            continue
                
                elif assignment_status == "stream_assigned" and stream_assignment:
                    # Stream assignment - use the assigned stream
                    actual_stream_id = db_stream_ids.get(stream_assignment, stream_assignment)
                    logger.info(f"  Stream assignment {stream_assignment} -> Stream ID: {actual_stream_id}")
                
                else:
                    logger.warning(f"  Client {client_id} has unclear assignment, skipping")
                    continue
                
                # Get group info for URL building
                try:
                    from ..group_management import get_group_by_id
                    group = get_group_by_id(group_id)
                except ImportError:
                    try:
                        from blueprints.group_management import get_group_by_id
                        group = get_group_by_id(group_id)
                    except ImportError:
                        logger.warning("Group management module not available")
                        group = None
                if not group:
                    logger.error(f"Group {group_id} not found")
                    continue
                
                # Get SRT IP
                srt_ip = client.get("srt_ip", os.getenv("SRT_SERVER_IP", "127.0.0.1"))
                
                # Build new stream URL
                stream_url = build_stream_url(group, actual_stream_id, group_name, srt_ip)
                
                # Update client with new stream information
                client["stream_id"] = actual_stream_id
                client["stream_url"] = stream_url
                client["stream_assignment"] = actual_stream_id  # Store the actual FFmpeg stream ID
                client["current_stream_ids"] = ffmpeg_stream_ids
                
                # Save updated client
                if hasattr(state, 'add_client'):
                    state.add_client(client_id, client)
                else:
                    state.clients[client_id] = client
                
                logger.info(f"✅ Updated client {client_id}:")
                logger.info(f"   Stream ID: {actual_stream_id}")
                logger.info(f"   Stream URL: {stream_url}")
                
            except Exception as e:
                logger.error(f"Error updating client {client_id}: {e}")
                continue
        
        logger.info(f"✅ COMPLETED: Updated {len(group_clients)} client assignments for group {group_name}")
        
    except Exception as e:
        logger.error(f"Error updating client assignments after restart: {e}")


    """
    Check if streaming is active for a group
    Clean import strategy with fallback
    """
    try:
        # Try to import the stream status check
        from ..streaming.split_stream import find_running_ffmpeg_for_group_strict
        processes = find_running_ffmpeg_for_group_strict(group_id, group_name, None)
        return len(processes) > 0
    except ImportError:
        try:
            # Try alternative import path
            from ..streaming.multi_stream import find_running_ffmpeg_for_group_strict
            processes = find_running_ffmpeg_for_group_strict(group_id, group_name, None)
            return len(processes) > 0
        except ImportError:
            logger.warning("Stream management not available, checking alternative way")
            # Try checking if FFmpeg is running with the group name
            try:
                import subprocess
                result = subprocess.run(['pgrep', '-f', f'live/{group_name}/'], capture_output=True)
                return result.returncode == 0
            except:
                # Assume streaming is active if we can't check
                logger.warning("Cannot verify streaming status, assuming active")
                return True
    except Exception as e:
        logger.error(f"Error checking streaming status: {e}")
        # Assume streaming is active if we can't check
        return True
    

def generate_stream_ids(group_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
    """Generate dynamic stream IDs for a session"""
    streams = {}
    
    # Generate a unique session ID based on current time and group
    session_id = str(uuid.uuid4())[:8]
    
    # Main/combined stream
    streams["test"] = f"{session_id}"
    
    # Individual screen streams
    for i in range(screen_count):
        streams[f"test{i}"] = f"{session_id}_{i}"
    
    return streams

def get_active_stream_ids_for_group(group_id: str, group_name: str, screen_count: int) -> Dict[str, str]:
    """
    Get current active stream IDs for a group
    Clean import strategy with graceful fallback
    """
    try:
        logger.info(f"Getting active stream IDs for group {group_name}")
        
        # Get group info
        group = get_group_from_docker(group_id)
        if not group:
            logger.error(f"Group {group_id} not found")
            return {}
        
        # Check if streaming is active
        container_id = group.get("container_id")
        is_streaming = check_streaming_status_for_group(group_id, group_name, container_id)
        
        if not is_streaming:
            logger.info(f"Group {group_name} is not currently streaming - no stream IDs available")
            return {}
        
        # Generate the SAME stream IDs that are actually being used
        stream_ids = generate_stream_ids(group_id, group_name, screen_count)
        
        logger.info(f"Active stream IDs for group {group_name}: {stream_ids}")
        return stream_ids
        
    except Exception as e:
        logger.error(f"Error getting active stream IDs: {e}")
        return {}

def build_stream_url_for_client(group: Dict[str, Any], stream_id: str, group_name: str, srt_ip: str = None) -> str:
    """
    Build SRT stream URL for a client
    FIXED: Complete URL format with proper error handling
    """
    try:
        # Use environment variable if srt_ip is not provided
        if srt_ip is None:
            srt_ip = os.getenv("SRT_SERVER_IP", "127.0.0.1")
        
        ports = group.get("ports", {})
        srt_port = ports.get("srt_port")
        
        if not srt_port:
            logger.error(f"No SRT port found for group {group_name}. Group ports: {ports}")
            srt_port = 10080
            logger.warning(f"Using fallback SRT port {srt_port} for group {group_name}")
        
        stream_path = f"live/{group_name}/{stream_id}"
        
        # FIXED: Complete SRT URL format with all required parameters
        stream_url = f"srt://{srt_ip}:{srt_port}?streamid=#!::r={stream_path},m=request,latency=5000000"
        
        logger.info(f"Built stream URL - Group: {group_name}, Stream ID: {stream_id}, Port: {srt_port}, URL: {stream_url}")
        
        return stream_url
        
    except Exception as e:
        logger.error(f"Error building stream URL: {e}")
        fallback_url = f"srt://{srt_ip}:10080?streamid=#!::r=live/{group_name}/{stream_id},m=request,latency=5000000"
        logger.warning(f"Using fallback URL: {fallback_url}")
        return fallback_url

# =====================================
# CLIENT ENDPOINTS
# =====================================

@log_function_call
def register_client():
    """
    Register a client device
    
    Expected payload:
    {
        "hostname": "display-001",
        "ip_address": "192.168.1.100",  # Optional, will use request IP
        "display_name": "Left Display",  # Optional
        "platform": "linux"  # Optional
    }
    """
    try:
        logger.info("==== CLIENT REGISTRATION REQUEST ====")
        
        # Import validators
        from .client_validators import validate_client_registration
        from .client_utils import get_next_steps
        
        # Get state
        state = get_state()
        
        # Parse and validate request data
        data = request.get_json()
        is_valid, error_msg, cleaned_data = validate_client_registration(data)
        
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
        
        # Extract validated data
        hostname = cleaned_data["hostname"]
        ip_address = cleaned_data["ip_address"] or request.remote_addr
        display_name = cleaned_data["display_name"]
        platform = cleaned_data["platform"]
        
        # Create unique client ID by combining hostname and IP address
        # This allows multiple terminal instances from the same device to run simultaneously
        client_id = f"{hostname}_{ip_address}"
        current_time = time.time()
        
        logger.info(f"Registering client: {client_id} (hostname: {hostname}, IP: {ip_address})")
        
        # Check for existing client
        existing_client = state.get_client(client_id) if hasattr(state, 'get_client') else state.clients.get(client_id)
        action = "updated" if existing_client else "registered"
        
        # Check for persistent assignment first
        from db.mongo import get_client_assignment, update_client_last_seen
        
        persistent_assignment = get_client_assignment(hostname)
        if persistent_assignment:
            logger.info(f"Found persistent assignment for {hostname}: group_id={persistent_assignment.get('group_id')}, screen_number={persistent_assignment.get('screen_number')}")
            
            # Update last seen timestamp
            update_client_last_seen(hostname)
            
            # Apply persistent assignment
            group_id = persistent_assignment.get("group_id")
            group_name = persistent_assignment.get("group_name")
            screen_number = persistent_assignment.get("screen_number")
            monitor_x = persistent_assignment.get("monitor_x")
            monitor_y = persistent_assignment.get("monitor_y")
            
            # Check if group still exists
            try:
                from ..group_management import get_group_by_id
                group = get_group_by_id(group_id)
            except ImportError:
                try:
                    from blueprints.group_management import get_group_by_id
                    group = get_group_by_id(group_id)
                except ImportError:
                    logger.warning("Group management module not available")
                    group = None
            if group:
                logger.info(f"Group {group_id} exists, applying persistent assignment")
                
                # Create client data with persistent assignment
                client_data = {
                    "client_id": client_id,
                    "hostname": hostname,
                    "ip_address": ip_address,
                    "display_name": display_name,
                    "platform": platform,
                    "registered_at": existing_client.get("registered_at", current_time) if existing_client else current_time,
                    "last_seen": current_time,
                    "status": "active",
                    "group_id": group_id,
                    "group_name": group_name,
                    "screen_number": screen_number,
                    "monitor_x": monitor_x,
                    "monitor_y": monitor_y,
                    "assignment_status": "screen_assigned" if screen_number is not None else "group_assigned",
                    "assigned_at": current_time,
                    "srt_ip": os.getenv("SRT_SERVER_IP", "127.0.0.1")
                }
                
                # Save client with persistent assignment
                if hasattr(state, 'add_client'):
                    state.add_client(client_id, client_data)
                elif hasattr(state, 'add_or_update_client'):
                    state.add_or_update_client(client_id, client_data)
                else:
                    state.clients[client_id] = client_data
                
                logger.info(f"Client {client_id} auto-assigned to group {group_name} (screen {screen_number})")
                
                return jsonify({
                    "success": True,
                    "message": f"Client auto-assigned to group {group_name} (screen {screen_number})",
                    "client_id": client_id,
                    "auto_assignment": {
                        "group_id": group_id,
                        "group_name": group_name,
                        "screen_number": screen_number,
                        "assignment_status": client_data["assignment_status"]
                    }
                }), 200
            else:
                logger.warning(f"Group {group_id} no longer exists, removing persistent assignment")
                from db.mongo import remove_client_assignment
                remove_client_assignment(hostname)
        
        # If client exists, preserve all existing data and just update heartbeat/status
        if existing_client:
            logger.info(f"Client {client_id} exists, preserving all existing data and updating heartbeat")
            logger.info(f"  Existing assignments: group_id={existing_client.get('group_id')}, assignment_status={existing_client.get('assignment_status')}, screen_number={existing_client.get('screen_number')}")
            
            # Preserve all existing data, only update heartbeat and status
            existing_client["last_seen"] = current_time
            existing_client["status"] = "active"
            existing_client["hostname"] = hostname  # Update hostname in case it changed
            existing_client["ip_address"] = ip_address  # Update IP in case it changed
            existing_client["display_name"] = display_name  # Update display name in case it changed
            existing_client["platform"] = platform  # Update platform in case it changed
            
            # Save the updated client
            if hasattr(state, 'add_client'):
                state.add_client(client_id, existing_client)
            elif hasattr(state, 'add_or_update_client'):
                state.add_or_update_client(client_id, existing_client)
            else:
                state.clients[client_id] = existing_client
            
            return jsonify({
                "success": True,
                "message": "Client reconnected, all assignments preserved",
                "client_id": client_id,
                "existing_assignments": {
                    "group_id": existing_client.get("group_id"),
                    "group_name": existing_client.get("group_name"),
                    "assignment_status": existing_client.get("assignment_status"),
                    "screen_number": existing_client.get("screen_number"),
                    "stream_assignment": existing_client.get("stream_assignment"),
                    "stream_url": existing_client.get("stream_url"),
                    "stream_id": existing_client.get("stream_id")
                }
            }), 200
        
        # Create or update client record
        client_data = {
            "client_id": client_id,
            "hostname": hostname,
            "ip_address": ip_address,
            "display_name": display_name,
            "platform": platform,
            "registered_at": existing_client.get("registered_at", current_time) if existing_client else current_time,
            "last_seen": current_time,
            "status": "active",
            
            # Group and stream assignment - preserve existing assignments only
            "group_id": existing_client.get("group_id") if existing_client else None,
            "group_name": existing_client.get("group_name") if existing_client else None,
            "stream_assignment": existing_client.get("stream_assignment") if existing_client else None,
            "stream_url": existing_client.get("stream_url") if existing_client else None,
            "screen_number": existing_client.get("screen_number") if existing_client else None,
            "assigned_at": existing_client.get("assigned_at") if existing_client else None,
            "srt_ip": existing_client.get("srt_ip", os.getenv("SRT_SERVER_IP", "127.0.0.1")) if existing_client else os.getenv("SRT_SERVER_IP", "127.0.0.1")
        }
        
        # Update assignment status based on current assignments
        if client_data["group_id"]:
            if client_data["screen_number"] is not None:
                client_data["assignment_status"] = "screen_assigned"
            elif client_data["stream_assignment"]:
                client_data["assignment_status"] = "stream_assigned"
            else:
                client_data["assignment_status"] = "group_assigned"
        else:
            # Only set to waiting_for_assignment if no existing assignments
            client_data["assignment_status"] = "waiting_for_assignment"
        
        # Save client
        if hasattr(state, 'add_client'):
            state.add_client(client_id, client_data)
        elif hasattr(state, 'add_or_update_client'):
            state.add_or_update_client(client_id, client_data)
        else:
            state.clients[client_id] = client_data
        
        logger.info(f"Client {action}: {client_id} (status: {client_data['assignment_status']})")
        
        # Debug: Verify client was saved
        logger.info(f"State type after save: {type(state)}")
        logger.info(f"State has clients after save: {hasattr(state, 'clients')}")
        if hasattr(state, 'clients'):
            logger.info(f"Available client IDs after save: {list(state.clients.keys())}")
            saved_client = state.clients.get(client_id)
            logger.info(f"Saved client data: {saved_client is not None}")
        
        # Prepare response
        response_data = {
            "success": True,
            "message": f"Client {action} successfully",
            "client_id": client_id,
            "action": action,
            "status": client_data["assignment_status"],
            "server_time": current_time,
            "next_steps": get_next_steps(client_data)
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Client registration failed: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Registration failed: {str(e)}"
        }), 500

def unregister_client():
    """Unregister a client"""
    try:
        data = request.get_json()
        client_id = data.get("client_id") if data else None
        
        if not client_id:
            return jsonify({
                "success": False,
                "error": "client_id is required"
            }), 400
        
        state = get_state()
        
        # Try different methods to remove client
        removed = False
        if hasattr(state, 'remove_client'):
            removed = state.remove_client(client_id)
        elif hasattr(state, 'clients'):
            if client_id in state.clients:
                del state.clients[client_id]
                removed = True
        
        if not removed:
            return jsonify({
                "success": False,
                "error": f"Client {client_id} not found"
            }), 404
        
        logger.info(f"Unregistered client: {client_id}")
        
        return jsonify({
            "success": True,
            "message": f"Client {client_id} unregistered successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Client unregistration failed: {e}")
        return jsonify({
            "success": False,
            "error": f"Unregistration failed: {str(e)}"
        }), 500

@log_function_call
def wait_for_assignment():
    """
    FIXED: Enhanced client endpoint to check assignment status and get stream URL when ready
    Handles both screen assignments and direct stream assignments
    """
    try:
        logger.info("==== WAIT FOR ASSIGNMENT REQUEST ====")
        
        # Import utilities from the same module
        from .client_utils import get_next_steps, build_stream_url, validate_stream_assignment
        # DON'T import get_state from client_state - use the one at top of file
        
        data = request.get_json() or {}
        client_id = data.get("client_id")
        
        logger.info(f"📋 WAIT FOR ASSIGNMENT DEBUG:")
        logger.info(f"   Request Data: {data}")
        logger.info(f"   Client ID: {client_id}")
        logger.info(f"   Request Headers: {dict(request.headers)}")
        
        if not client_id:
            logger.error("❌ WAIT FOR ASSIGNMENT FAILED: No client_id provided")
            return jsonify({
                "success": False,
                "status": "error",
                "message": "client_id is required"
            }), 400
        
        state = get_state()  # Use the function defined at top of file
        logger.info(f"🔍 STATE DEBUG:")
        logger.info(f"   State Type: {type(state)}")
        logger.info(f"   State Has Clients: {hasattr(state, 'clients')}")
        if hasattr(state, 'clients'):
            logger.info(f"   Available Client IDs: {list(state.clients.keys())}")
            logger.info(f"   Total Clients: {len(state.clients)}")
        
        client = state.get_client(client_id) if hasattr(state, 'get_client') else state.clients.get(client_id)
        
        logger.info(f"🔍 CLIENT LOOKUP DEBUG:")
        logger.info(f"   Client Found: {client is not None}")
        if client:
            logger.info(f"   Client Data: {client}")
            logger.info(f"   Client Assignment Status: {client.get('assignment_status', 'unknown')}")
            logger.info(f"   Client Group ID: {client.get('group_id', 'none')}")
            logger.info(f"   Client Stream Assignment: {client.get('stream_assignment', 'none')}")
            logger.info(f"   Client Screen Number: {client.get('screen_number', 'none')}")
        
        if not client:
            logger.error(f"❌ WAIT FOR ASSIGNMENT FAILED: Client {client_id} not found")
            return jsonify({
                "success": False,
                "status": "not_registered", 
                "message": "Client not found. Please register first."
            }), 404
        
        # Update client heartbeat to show it's still active
        current_time = time.time()
        client["last_seen"] = current_time
        client["status"] = "active"
        
        # Save the updated client data
        if hasattr(state, 'add_client'):
            state.add_client(client_id, client)
        elif hasattr(state, 'add_or_update_client'):
            state.add_or_update_client(client_id, client)
        else:
            state.clients[client_id] = client
        
        # Get assignment status
        assignment_status = client.get("assignment_status", "waiting_for_assignment")
        group_id = client.get("group_id")
        
        logger.info(f" Client {client_id} checking assignment (heartbeat updated):")
        logger.info(f"   - Assignment status: {assignment_status}")
        logger.info(f"   - Group ID: {group_id}")
        logger.info(f"   - Last seen updated to: {current_time}")
        logger.info(f"   - Full client data: {client}")
        
        # Case 1: Waiting for group assignment
        if assignment_status == "waiting_for_assignment" or not group_id:
            logger.info(f" Client {client_id} is waiting for group assignment or has no group")
            return jsonify({
                "success": False,
                "status": "waiting_for_assignment",
                "message": "Waiting for admin to assign you to a group",
                "next_steps": get_next_steps(client)
            }), 202
        
        # Get group information - FIX THE IMPORT HERE
        group = None
        if group_id:
            try:
                # Try to import and use discover_groups (same as admin_endpoints does)
                from ..docker_management import discover_groups
                discovery_result = discover_groups()
                if discovery_result.get("success", False):
                    for g in discovery_result.get("groups", []):
                        if g.get("id") == group_id:
                            group = g
                            logger.info(f"Found group {group_id} in Docker")
                            break
            except ImportError as e:
                logger.warning(f"Docker management import failed: {e}")
            except Exception as e:
                logger.warning(f"Error discovering groups: {e}")
            
            # If we couldn't find the group, create a mock one
            if not group:
                logger.warning(f"Using mock group for {group_id}")
                group = {
                    "id": group_id,
                    "name": f"Group-{group_id[:8]}",
                    "docker_running": True,
                    "container_id": f"mock-{group_id[:8]}",
                    "ports": {"srt_port": 10080}
                }
        
        if not group:
            return jsonify({
                "success": False,
                "status": "group_not_found",
                "message": f"Group {group_id} not found or not running",
                "group_id": group_id
            }), 202
        
        group_name = group.get("name", group_id)
        
        # Case 2: Group assigned but no stream assignment
        if assignment_status == "group_assigned":
            logger.info(f" Client {client_id} has group but no stream/screen assignment")
            return jsonify({
                "success": False,
                "status": "waiting_for_stream_assignment",
                "message": "Waiting for admin to assign you to a specific stream or screen",
                "group_id": group_id,
                "group_name": group_name,
                "next_steps": get_next_steps(client)
            }), 202
        
        # Case 3: Stream or screen assigned - check if streaming
        if assignment_status in ["stream_assigned", "screen_assigned"]:
            logger.info(f" Client {client_id} has stream/screen assignment, checking streaming status")
            # Check if group is streaming
            container_id = group.get("container_id")
            
            # Check if group is streaming
            is_streaming = False
            
            try:
                # Try to check if FFmpeg is running
                from ..streaming.split_stream import find_running_ffmpeg_for_group_strict
                processes = find_running_ffmpeg_for_group_strict(group_id, group_name, group.get("container_id"))
                is_streaming = len(processes) > 0
                logger.info(f" FFmpeg check for group {group_name}: {len(processes)} processes found, is_streaming={is_streaming}")
            except ImportError as e:
                logger.warning(f"Import error checking streaming status: {e}")
                # Try alternative import path
                try:
                    from ..streaming.multi_stream import find_running_ffmpeg_for_group_strict
                    processes = find_running_ffmpeg_for_group_strict(group_id, group_name, group.get("container_id"))
                    is_streaming = len(processes) > 0
                    logger.info(f" FFmpeg check (alt import) for group {group_name}: {len(processes)} processes found, is_streaming={is_streaming}")
                except ImportError as e2:
                    logger.warning(f"Both streaming imports failed, using fallback: {e2}")
                    # Fallback function if import fails
                    def find_running_ffmpeg_for_group_strict(group_id: str, group_name: str, container_id: str):
                        """Find running FFmpeg processes for a group"""
                        return []
                    processes = find_running_ffmpeg_for_group_strict(group_id, group_name, group.get("container_id"))
                    is_streaming = len(processes) > 0
                    logger.info(f" FFmpeg check (fallback) for group {group_name}: {len(processes)} processes found, is_streaming={is_streaming}")
            except Exception as e:
                logger.error(f"Error checking streaming status: {e}")
                is_streaming = False
            
            if not is_streaming:
                return jsonify({
                    "success": False,
                    "status": "waiting_for_streaming",
                    "message": "Waiting for streaming to start",
                    "group_id": group_id,
                    "group_name": group_name,
                    "stream_assignment": client.get("stream_assignment"),
                    "screen_number": client.get("screen_number"),
                    "assignment_status": assignment_status,
                    "next_steps": get_next_steps(client)
                }), 202
            
            # Streaming is active - prepare stream URL
            stream_url = client.get("stream_url")
            
            # Get current active stream IDs from running FFmpeg process
            current_stream_ids = {}
            try:
                from ..streaming.multi_stream import get_active_stream_ids
                current_stream_ids = get_active_stream_ids(group_id)
                logger.info(f" Current active stream IDs: {current_stream_ids}")
            except ImportError:
                try:
                    from ..streaming.split_stream import get_active_stream_ids
                    current_stream_ids = get_active_stream_ids(group_id)
                    logger.info(f" Current active stream IDs (split): {current_stream_ids}")
                except ImportError:
                    logger.warning("Could not import streaming modules to get active stream IDs")
                    current_stream_ids = {}
            
            # Only rebuild stream URL if client doesn't have one or if stream IDs have changed
            should_rebuild = False
            
            # Check if client already has a valid stream URL and stream ID
            existing_stream_url = client.get("stream_url")
            existing_stream_id = client.get("stream_id")
            
            if not existing_stream_url or not existing_stream_id:
                logger.info(f" Client {client_id} missing stream URL or ID, rebuilding...")
                should_rebuild = True
            elif existing_stream_id.startswith("screen"):
                logger.error(f" Client {client_id} has invalid stream ID ({existing_stream_id}) - streaming may not be active")
                return jsonify({
                    "success": False,
                    "status": "invalid_stream_id",
                    "message": f"Client has invalid stream ID ({existing_stream_id}). Streaming may not be active.",
                    "group_id": group_id,
                    "group_name": group_name,
                    "client_id": client_id
                }), 503
            elif existing_stream_url and "screen" in existing_stream_url and not existing_stream_id.startswith("screen"):
                # Client has correct stream ID but old format stream URL - rebuild needed
                logger.info(f" Client {client_id} has correct stream ID ({existing_stream_id}) but old format stream URL, rebuilding...")
                should_rebuild = True
            else:
                logger.info(f" Client {client_id} already has valid stream ID ({existing_stream_id}) and URL, skipping rebuild")
                should_rebuild = False
            
            if should_rebuild:
                if assignment_status == "screen_assigned":
                    # For screen assignment, use the correct stream ID format that matches FFmpeg
                    screen_number = client.get("screen_number", 0)
                    
                    # Use database stream IDs instead of extracting from FFmpeg
                    from db.mongo import get_group_stream_ids
                    db_stream_ids = get_group_stream_ids(group_id)
                    
                    if db_stream_ids:
                        logger.info(f" Using stream IDs from database: {db_stream_ids}")
                        screen_key = f"test{screen_number}"
                        
                        if screen_key in db_stream_ids:
                            actual_stream_id = db_stream_ids[screen_key]
                            logger.info(f" Using database stream ID for screen {screen_number}: {actual_stream_id}")
                        else:
                            # Try to construct from base stream ID
                            base_stream_id = db_stream_ids.get("base")
                            if base_stream_id:
                                actual_stream_id = f"{base_stream_id}_{screen_number}"
                                logger.info(f" Constructed stream ID from database base: {actual_stream_id}")
                            else:
                                # No database stream IDs found - return error instead of fallback
                                logger.error(f" No database stream IDs found for screen {screen_number}")
                                return jsonify({
                                    "success": False,
                                    "status": "stream_id_not_found",
                                    "message": f"No database stream IDs found for screen {screen_number}. Streaming may not be active.",
                                    "group_id": group_id,
                                    "group_name": group_name,
                                    "screen_number": screen_number
                                }), 503
                    else:
                        logger.error(f" No database stream IDs found for group {group_id}")
                        return jsonify({
                            "success": False,
                            "status": "stream_id_not_found",
                            "message": f"No database stream IDs found for group {group_id}. Streaming may not be active.",
                            "group_id": group_id,
                            "group_name": group_name,
                            "screen_number": screen_number
                        }), 503
                else:
                    # For stream assignment, use the assigned stream
                    actual_stream_id = client.get("stream_assignment", "default")
                
                # Get SRT IP from client or use default
                srt_ip = client.get("srt_ip", os.getenv("SRT_SERVER_IP", "127.0.0.1"))
                
                # Build the stream URL with the actual stream ID
                stream_url = build_stream_url(group, actual_stream_id, group_name, srt_ip)
                
                # Update client with stream URL, stream ID, and current stream IDs
                client["stream_url"] = stream_url
                client["stream_id"] = actual_stream_id
                client["stream_assignment"] = actual_stream_id  # Store the actual FFmpeg stream ID
                client["current_stream_ids"] = current_stream_ids
                if hasattr(state, 'add_client'):
                    state.add_client(client_id, client)
                else:
                    state.clients[client_id] = client
            else:
                # Use existing stream URL and ID without rebuilding
                stream_url = existing_stream_url
                actual_stream_id = existing_stream_id
                logger.info(f" Using existing stream URL and ID for client {client_id}")
            
            # Enhanced validation before returning ready status
            logger.info(f"🔍 RUNNING STREAM ASSIGNMENT VALIDATION...")
            validation_result = validate_stream_assignment(client, actual_stream_id, stream_url, group_name)
            logger.info(f"   Validation Result: {validation_result}")
            
            # Return ready to play status with validation info
            response_data = {
                "success": True,
                "status": "ready_to_play",
                "message": "Stream is ready",
                "stream_id": actual_stream_id,
                "stream_url": stream_url,
                "group_id": group_id,
                "group_name": group_name,
                "stream_assignment": client.get("stream_assignment"),
                "screen_number": client.get("screen_number"),
                "assignment_status": assignment_status,
                "stream_version": client.get("stream_version", None),
                "validation": validation_result
            }
            
            if not validation_result["is_valid"]:
                logger.warning(f"⚠️ STREAM VALIDATION FAILED: Client {client_id}: {validation_result['errors']}")
                response_data["warnings"] = validation_result["errors"]
            else:
                logger.info(f"✅ STREAM VALIDATION PASSED: Client {client_id}")
            
            logger.info(f"📤 READY TO PLAY RESPONSE DEBUG:")
            logger.info(f"   Response Data: {response_data}")
            logger.info(f"   Response Size: {len(str(response_data))} characters")
            
            return jsonify(response_data), 200
        
        # Unknown status
        logger.warning(f" Client {client_id} has unknown assignment status: {assignment_status}")
        return jsonify({
            "success": False,
            "status": "unknown",
            "message": f"Unknown assignment status: {assignment_status}",
            "assignment_status": assignment_status
        }), 202
        
    except Exception as e:
        logger.error(f"Error in wait_for_assignment: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500


@log_function_call
def client_heartbeat():
    """
    Client heartbeat endpoint to keep connection alive and handle stream updates
    Updates last_seen timestamp for the client and returns current stream info
    """
    try:
        logger.info("==== CLIENT HEARTBEAT REQUEST ====")
        
        data = request.get_json() or {}
        client_id = data.get("client_id")
        current_stream_id = data.get("current_stream_id")
        current_stream_url = data.get("current_stream_url")
        current_stream_version = data.get("current_stream_version")
        
        logger.info(f"🔔 HEARTBEAT DEBUG - Received heartbeat from client:")
        logger.info(f"   Client ID: {client_id}")
        logger.info(f"   Current Stream ID: {current_stream_id}")
        logger.info(f"   Current Stream URL: {current_stream_url}")
        logger.info(f"   Current Stream Version: {current_stream_version}")
        logger.info(f"   Full Request Data: {data}")
        
        if not client_id:
            logger.error("❌ HEARTBEAT FAILED: No client_id provided")
            return jsonify({
                "success": False,
                "error": "client_id is required"
            }), 400
        
        state = get_state()
        client = state.get_client(client_id) if hasattr(state, 'get_client') else state.clients.get(client_id)
        
        logger.info(f"🔍 CLIENT LOOKUP DEBUG:")
        logger.info(f"   State Type: {type(state)}")
        logger.info(f"   Client Found: {client is not None}")
        if client:
            logger.info(f"   Client Data: {client}")
        
        if not client:
            logger.error(f"❌ HEARTBEAT FAILED: Client {client_id} not found")
            return jsonify({
                "success": False,
                "error": "Client not found. Please register first."
            }), 404
        
        # Update heartbeat
        current_time = time.time()
        client["last_seen"] = current_time
        client["status"] = "active"
        
        # Auto-fix SRT IP if it's wrong
        correct_srt_ip = os.getenv("SRT_SERVER_IP", "128.205.111.40")
        current_srt_ip = client.get("srt_ip", "127.0.0.1")
        srt_ip_corrected = False
        
        if current_srt_ip != correct_srt_ip:
            logger.info(f"🔧 AUTO-FIXING SRT IP:")
            logger.info(f"   Current SRT IP: {current_srt_ip}")
            logger.info(f"   Correct SRT IP: {correct_srt_ip}")
            
            # Update client's SRT IP
            client["srt_ip"] = correct_srt_ip
            srt_ip_corrected = True
            
            # If client has a stream URL, rebuild it with correct IP
            if client.get("stream_url") and client.get("group_id"):
                try:
                    from .client_utils import build_stream_url
                    from ..group_management import get_group_by_id
                    
                    group_id = client.get("group_id")
                    group_name = client.get("group_name", "unknown")
                    stream_id = client.get("stream_id")
                    
                    if stream_id:
                        group = get_group_by_id(group_id)
                        if group:
                            new_stream_url = build_stream_url(group, stream_id, group_name, correct_srt_ip)
                            client["stream_url"] = new_stream_url
                            logger.info(f"   Updated stream URL: {new_stream_url}")
                except Exception as e:
                    logger.warning(f"   Could not update stream URL: {e}")
            
            # Save updated client
            if hasattr(state, 'add_client'):
                state.add_client(client_id, client)
            else:
                state.clients[client_id] = client
            
            logger.info(f"   ✅ SRT IP auto-corrected to {correct_srt_ip}")
        
        logger.info(f"📊 CLIENT STATUS UPDATE:")
        logger.info(f"   Last Seen: {current_time}")
        logger.info(f"   Status: active")
        
        # Check if client's stream has changed
        server_stream_id = client.get("stream_id")
        server_stream_url = client.get("stream_url")
        server_stream_version = client.get("stream_version")
        
        logger.info(f"🔍 STREAM COMPARISON DEBUG:")
        logger.info(f"   Client Stream ID: {current_stream_id}")
        logger.info(f"   Server Stream ID: {server_stream_id}")
        logger.info(f"   Client Stream URL: {current_stream_url}")
        logger.info(f"   Server Stream URL: {server_stream_url}")
        logger.info(f"   Client Stream Version: {current_stream_version}")
        logger.info(f"   Server Stream Version: {server_stream_version}")
        
        # Enhanced stream validation
        stream_validation = {
            "is_valid": True,
            "warnings": [],
            "mismatches": []
        }
        
        logger.info(f"🔍 RUNNING STREAM VALIDATION...")
        
        # Validate stream ID consistency
        if current_stream_id and server_stream_id:
            if current_stream_id != server_stream_id:
                stream_validation["is_valid"] = False
                stream_validation["mismatches"].append({
                    "type": "stream_id",
                    "client": current_stream_id,
                    "server": server_stream_id
                })
                logger.warning(f"❌ STREAM ID MISMATCH: Client {client_id} stream ID mismatch: client={current_stream_id}, server={server_stream_id}")
            else:
                logger.info(f"✅ Stream ID validation passed")
        else:
            logger.info(f"ℹ️ Skipping stream ID validation - missing data")
        
        # Validate stream URL consistency
        if current_stream_url and server_stream_url:
            if current_stream_url != server_stream_url:
                stream_validation["warnings"].append({
                    "type": "stream_url",
                    "client": current_stream_url,
                    "server": server_stream_url
                })
                logger.warning(f"⚠️ STREAM URL MISMATCH: Client {client_id} stream URL mismatch: client={current_stream_url}, server={server_stream_url}")
            else:
                logger.info(f"✅ Stream URL validation passed")
        else:
            logger.info(f"ℹ️ Skipping stream URL validation - missing data")
        
        # Validate stream version consistency
        if current_stream_version and server_stream_version:
            if current_stream_version != server_stream_version:
                stream_validation["warnings"].append({
                    "type": "stream_version",
                    "client": current_stream_version,
                    "server": server_stream_version
                })
                logger.warning(f"⚠️ STREAM VERSION MISMATCH: Client {client_id} stream version mismatch: client={current_stream_version}, server={server_stream_version}")
            else:
                logger.info(f"✅ Stream version validation passed")
        else:
            logger.info(f"ℹ️ Skipping stream version validation - missing data")
        
        # Log stream status with validation results
        logger.info(f"📊 STREAM VALIDATION SUMMARY:")
        logger.info(f"   Client {client_id} heartbeat - Current stream: {current_stream_id} -> Server stream: {server_stream_id}")
        logger.info(f"   Validation Result: valid={stream_validation['is_valid']}, warnings={len(stream_validation['warnings'])}, mismatches={len(stream_validation['mismatches'])}")
        
        if stream_validation['mismatches']:
            logger.warning(f"   Mismatches: {stream_validation['mismatches']}")
        if stream_validation['warnings']:
            logger.warning(f"   Warnings: {stream_validation['warnings']}")
        
        # Save updated client data
        if hasattr(state, 'add_client'):
            state.add_client(client_id, client)
        elif hasattr(state, 'add_or_update_client'):
            state.add_or_update_client(client_id, client)
        else:
            state.clients[client_id] = client
        
        logger.info(f"Client {client_id} heartbeat updated: {current_time}")
        
        # Return current stream information for client to check for updates
        response_data = {
            "success": True,
            "message": "Heartbeat received",
            "client_id": client_id,
            "timestamp": current_time,
            "status": "active",
            "stream_validation": stream_validation,
            "srt_ip_corrected": srt_ip_corrected
        }
        
        # Include current stream information if client has assignments
        if server_stream_id:
            response_data["stream_id"] = server_stream_id
        if server_stream_url:
            response_data["stream_url"] = server_stream_url
        if server_stream_version:
            response_data["stream_version"] = server_stream_version
        if client.get("assignment_status"):
            response_data["assignment_status"] = client["assignment_status"]
        if client.get("group_name"):
            response_data["group_name"] = client["group_name"]
        if client.get("stream_assignment"):
            response_data["stream_assignment"] = client["stream_assignment"]
        if client.get("screen_number") is not None:
            response_data["screen_number"] = client["screen_number"]
        
        logger.info(f"📤 HEARTBEAT RESPONSE DEBUG:")
        logger.info(f"   Response Data: {response_data}")
        logger.info(f"   Response Size: {len(str(response_data))} characters")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error in client_heartbeat: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@log_function_call
def kill_old_stream():
    """
    Client requests server to kill an old stream that it's no longer using
    """
    try:
        logger.info("==== KILL OLD STREAM REQUEST ====")
        
        data = request.get_json() or {}
        client_id = data.get("client_id")
        old_stream_id = data.get("old_stream_id")
        
        if not client_id:
            return jsonify({
                "success": False,
                "error": "client_id is required"
            }), 400
            
        if not old_stream_id:
            return jsonify({
                "success": False,
                "error": "old_stream_id is required"
            }), 400
        
        state = get_state()
        client = state.get_client(client_id) if hasattr(state, 'get_client') else state.clients.get(client_id)
        
        if not client:
            return jsonify({
                "success": False,
                "error": "Client not found"
            }), 404
        
        logger.info(f"Client {client_id} requesting to kill old stream: {old_stream_id}")
        
        # TODO: Implement actual stream killing logic here
        # For now, just log the request
        logger.info(f"Old stream kill request received for stream {old_stream_id} from client {client_id}")
        
        return jsonify({
            "success": True,
            "message": f"Old stream {old_stream_id} kill request received",
            "client_id": client_id,
            "old_stream_id": old_stream_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error in kill_old_stream: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


def unassign_client_from_screen():
    """
    Admin function: Remove a client's screen assignment (frees up the screen for another client)
    """
    try:
        logger.info("==== UNASSIGN CLIENT FROM SCREEN REQUEST RECEIVED ====")
        
        state = get_state()
        data = request.get_json() or {}
        
        client_id = data.get("client_id")
        
        if not client_id:
            return jsonify({
                "success": False,
                "error": "client_id is required"
            }), 400
        
        # Check if state has clients attribute
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        if client_id not in state.clients:
            return jsonify({
                "success": False,
                "error": "Client not found"
            }), 404
        
        # Handle state with or without lock
        if hasattr(state, 'clients_lock'):
            with state.clients_lock:
                client = state.clients[client_id]
                old_group_id = client.get("group_id")
                old_screen_number = client.get("screen_number")
                old_stream = client.get("stream_assignment")
                
                # Clear screen assignment but keep group assignment
                client.update({
                    "screen_number": None,
                    "stream_assignment": None,
                    "stream_url": None,
                    "assignment_status": "assigned_to_group",  # Still in group, just no specific screen
                    "unassigned_at": time.time()
                })
        else:
            # No lock available, update directly
            client = state.clients[client_id]
            old_group_id = client.get("group_id")
            old_screen_number = client.get("screen_number")
            old_stream = client.get("stream_assignment")
            
            # Clear screen assignment but keep group assignment
            client.update({
                "screen_number": None,
                "stream_assignment": None,
                "stream_url": None,
                "assignment_status": "assigned_to_group",  # Still in group, just no specific screen
                "unassigned_at": time.time()
            })
        
        logger.info(f" Unassigned client {client_id} from screen {old_screen_number} in group {old_group_id}")
        
        return jsonify({
            "success": True,
            "message": f"Client {client_id} unassigned from screen {old_screen_number}",
            "client_id": client_id,
            "group_id": old_group_id,
            "old_screen_number": old_screen_number,
            "old_stream": old_stream,
            "assignment_status": "assigned_to_group"
        }), 200
        
    except Exception as e:
        logger.error(f"Error unassigning client from screen: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def unassign_client_from_stream():
    """
    Admin function: Remove a client's stream assignment (frees up the stream for another client)
    """
    try:
        logger.info("==== UNASSIGN CLIENT FROM STREAM REQUEST RECEIVED ====")
        
        state = get_state()
        data = request.get_json() or {}
        
        client_id = data.get("client_id")
        
        if not client_id:
            return jsonify({
                "success": False,
                "error": "client_id is required"
            }), 400
        
        # Check if state has clients attribute
        if not hasattr(state, 'clients'):
            state.clients = {}
        
        if client_id not in state.clients:
            return jsonify({
                "success": False,
                "error": "Client not found"
            }), 404
        
        # Handle state with or without lock
        if hasattr(state, 'clients_lock'):
            with state.clients_lock:
                client = state.clients[client_id]
                old_group_id = client.get("group_id")
                old_stream = client.get("stream_assignment")
                old_screen_number = client.get("screen_number")
                
                # Clear stream assignment but keep group assignment
                client.update({
                    "stream_assignment": None,
                    "stream_url": None,
                    "assignment_status": "assigned_to_group" if old_group_id else "waiting_for_assignment",
                    "unassigned_at": time.time()
                })
        else:
            # No lock available, update directly
            client = state.clients[client_id]
            old_group_id = client.get("group_id")
            old_stream = client.get("stream_assignment")
            old_screen_number = client.get("screen_number")
            
            # Clear stream assignment but keep group assignment
            client.update({
                "stream_assignment": None,
                "stream_url": None,
                "assignment_status": "assigned_to_group" if old_group_id else "waiting_for_assignment",
                "unassigned_at": time.time()
            })
        
        logger.info(f" Unassigned client {client_id} from stream {old_stream} in group {old_group_id}")
        
        return jsonify({
            "success": True,
            "message": f"Client {client_id} unassigned from stream {old_stream}",
            "client_id": client_id,
            "group_id": old_group_id,
            "old_stream": old_stream,
            "old_screen_number": old_screen_number,
            "assignment_status": client.get("assignment_status")
        }), 200
        
    except Exception as e:
        logger.error(f"Error unassigning client from stream: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def resolve_stream_urls_for_group(group_id: str, group_name: str):
    """
    FIXED: Called when streaming starts - resolves stream URLs for all assigned clients
    Ensures all clients get properly formatted stream URLs
    """
    try:
        logger.info(f" Resolving stream URLs for all clients assigned to group {group_name}")
        
        state = get_state()
        all_clients = state.get_all_clients() if hasattr(state, 'get_all_clients') else state.clients
        
        # Find clients assigned to this group
        group_clients = []
        for client_id, client in all_clients.items():
            if client.get("group_id") == group_id and client.get("assignment_status") == "screen_assigned":
                group_clients.append((client_id, client))
        
        if not group_clients:
            logger.info(f"No clients assigned to group {group_name}")
            return
        
        # Get current active stream IDs
        group = get_group_from_docker(group_id)
        if not group:
            logger.error(f"Group {group_id} not found")
            return
        
        # Try to get stream IDs from database first (most reliable)
        try:
            from db.mongo import get_group_stream_ids
            active_stream_ids = get_group_stream_ids(group_id)
            if active_stream_ids:
                logger.info(f" Using database stream IDs: {active_stream_ids}")
            else:
                logger.warning(f" No database stream IDs found for group {group_name}, trying other sources...")
                # Fallback to other methods if database doesn't have stream IDs
                try:
                    try:
                        from blueprints.streaming.split_stream import get_active_stream_ids
                    except ImportError:
                        try:
                            from blueprints.streaming.multi_stream import get_active_stream_ids
                        except ImportError:
                            # Fallback function if import fails
                            def get_active_stream_ids(group_id: str):
                                """Get active stream IDs for a group"""
                                return {}
                    
                    active_stream_ids = get_active_stream_ids(group_id)
                    if active_stream_ids:
                        logger.info(f" Using active stream IDs: {active_stream_ids}")
                    else:
                        # Fallback: try group metadata
                        active_stream_ids = group.get("stream_ids", {})
                        if active_stream_ids:
                            logger.info(f" Using group metadata stream IDs: {active_stream_ids}")
                        else:
                            # Last resort: generate stream IDs
                            try:
                                from blueprints.streaming.split_stream import generate_stream_ids
                            except ImportError:
                                try:
                                    from blueprints.streaming.multi_stream import generate_stream_ids
                                except ImportError:
                                    # Fallback function if import fails
                                    def generate_stream_ids(base_stream_id: str, group_name: str, screen_count: int):
                                        """Generate stream IDs for a group"""
                                        stream_ids = {}
                                        
                                        # Combined stream ID
                                        stream_ids["test"] = f"{base_stream_id[:8]}"
                                        
                                        # Individual screen stream IDs
                                        for i in range(screen_count):
                                            stream_ids[f"test{i}"] = f"{base_stream_id[:8]}_{i}"
                                        
                                        return stream_ids
                            screen_count = group.get("screen_count", 2)
                            active_stream_ids = generate_stream_ids(group_id, group_name, screen_count)
                            logger.info(f" Generated fallback stream IDs: {active_stream_ids}")
                except Exception as e2:
                    logger.error(f"Error getting fallback stream IDs: {e2}")
                    return
        except Exception as e:
            logger.error(f"Error getting active stream IDs: {e}")
            return
        
        # Update each client with resolved stream URL
        updated_count = 0
        for client_id, client in group_clients:
            screen_number = client.get("screen_number")
            if screen_number is not None:
                screen_stream_key = f"test{screen_number}"
                if screen_stream_key in active_stream_ids:
                    stream_id = active_stream_ids[screen_stream_key]
                    srt_ip = client.get("srt_ip", os.getenv("SRT_SERVER_IP", "127.0.0.1"))
                    
                    # FIXED: Use the corrected build function
                    stream_url = build_stream_url_for_client(group, stream_id, group_name, srt_ip)
                    
                    # Update client
                    client["stream_url"] = stream_url
                    client["stream_version"] = int(time.time())
                    if hasattr(state, 'add_client'):
                        state.add_client(client_id, client)
                    else:
                        state.clients[client_id] = client
                    
                    logger.info(f" Resolved URL for client {client_id}  screen {screen_number}  {stream_id}")
                    logger.info(f"   Full URL: {stream_url}")
                    updated_count += 1
        
        logger.info(f" Resolved stream URLs for {updated_count}/{len(group_clients)} clients in group {group_name}")
        
    except Exception as e:
        logger.error(f"Error resolving stream URLs for group {group_name}: {e}")
        import traceback
        traceback.print_exc()

# Legacy endpoints for backwards compatibility
def register_client_legacy():
    """Legacy endpoint - redirects to new register endpoint"""
    return register_client()

def wait_for_stream_legacy():
    """Legacy endpoint - redirects to new wait_for_assignment endpoint"""
    return wait_for_assignment()