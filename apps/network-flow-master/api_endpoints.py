"""
Additional API endpoints for the FlowVision application
"""
import os
import json
import time
import platform
import psutil
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import func, desc, case, distinct, and_
from database import db
import analyzer
from ai_insights import get_ai_insights_manager

# Create blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route('/api/status', methods=['GET'])
def api_status():
    """API status endpoint"""
    return jsonify({
        'status': 'operational',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'api_endpoints': [
            '/api/status',
            '/api/stats/summary',
            '/api/flows',
            '/api/devices',
            '/api/device/<id>',
            '/api/ai/insights/<device_id>',
            '/api/ai/anomalies',
            '/api/forwards',
            '/api/forward/<id>',
            '/api/mibs',
            '/api/mib/<id>',
            '/api/forwarder_stats'
        ]
    }), 200



@api_bp.route('/api/stats/summary', methods=['GET'])
def api_stats_summary():
    """Summary statistics for the API"""
    from models import FlowData, Device, ForwardTarget
    
    # Get date range parameters
    start_date = request.args.get('start_date', 
                                 (datetime.utcnow() - timedelta(days=1)).isoformat())
    end_date = request.args.get('end_date', datetime.utcnow().isoformat())
    
    # Convert to datetime if they're strings
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date)
    
    # Get the number of devices
    device_count = db.session.query(func.count(Device.id)).scalar()
    
    # Get the number of flows in the time range
    flow_count = db.session.query(func.count(FlowData.id)).filter(
        FlowData.timestamp.between(start_date, end_date)
    ).scalar()
    
    # Get the breakdown by flow type
    flow_types = db.session.query(
        FlowData.flow_type,
        func.count(FlowData.id)
    ).filter(
        FlowData.timestamp.between(start_date, end_date)
    ).group_by(FlowData.flow_type).all()
    
    # Format flow types
    flow_type_summary = {}
    for flow_type, count in flow_types:
        flow_type_summary[flow_type] = count
    
    # Get the top talkers (src_ip)
    top_talkers = db.session.query(
        FlowData.src_ip,
        func.sum(FlowData.bytes).label('total_bytes'),
        func.count(FlowData.id).label('flow_count')
    ).filter(
        FlowData.timestamp.between(start_date, end_date)
    ).group_by(FlowData.src_ip).order_by(desc('total_bytes')).limit(10).all()
    
    # Format top talkers
    top_talkers_summary = []
    for ip, bytes, count in top_talkers:
        top_talkers_summary.append({
            'ip': ip,
            'bytes': bytes,
            'flow_count': count
        })
    
    # Get the top destinations (dst_ip)
    top_destinations = db.session.query(
        FlowData.dst_ip,
        func.sum(FlowData.bytes).label('total_bytes'),
        func.count(FlowData.id).label('flow_count')
    ).filter(
        FlowData.timestamp.between(start_date, end_date)
    ).group_by(FlowData.dst_ip).order_by(desc('total_bytes')).limit(10).all()
    
    # Format top destinations
    top_destinations_summary = []
    for ip, bytes, count in top_destinations:
        top_destinations_summary.append({
            'ip': ip,
            'bytes': bytes,
            'flow_count': count
        })
    
    # Get protocol distribution
    protocols = db.session.query(
        FlowData.protocol,
        func.count(FlowData.id).label('flow_count')
    ).filter(
        FlowData.timestamp.between(start_date, end_date)
    ).group_by(FlowData.protocol).all()
    
    # Format protocols
    protocol_summary = {}
    for protocol, count in protocols:
        protocol_name = get_protocol_name(protocol)
        protocol_summary[protocol_name] = count
    
    # Get hourly distribution
    hourly_distribution = db.session.query(
        func.extract('hour', FlowData.timestamp).label('hour'),
        func.count(FlowData.id).label('flow_count')
    ).filter(
        FlowData.timestamp.between(start_date, end_date)
    ).group_by('hour').order_by('hour').all()
    
    # Format hourly distribution
    hourly_summary = {}
    for hour, count in hourly_distribution:
        hourly_summary[int(hour)] = count
    
    # Get data volume over time (in 1-hour intervals)
    time_series = db.session.query(
        func.date_trunc('hour', FlowData.timestamp).label('hour'),
        func.sum(FlowData.bytes).label('bytes'),
        func.sum(FlowData.packets).label('packets'),
        func.count(FlowData.id).label('flows')
    ).filter(
        FlowData.timestamp.between(start_date, end_date)
    ).group_by('hour').order_by('hour').all()
    
    # Format time series
    time_series_summary = []
    for hour, bytes, packets, flows in time_series:
        time_series_summary.append({
            'timestamp': hour.isoformat(),
            'bytes': bytes,
            'packets': packets,
            'flows': flows
        })
    
    # Get forward target stats
    forward_targets = db.session.query(
        func.count(ForwardTarget.id),
        func.sum(case([(ForwardTarget.active == True, 1)], else_=0))
    ).first()
    
    # Compile the response
    response = {
        'time_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        },
        'summary': {
            'device_count': device_count,
            'flow_count': flow_count,
            'forward_targets': {
                'total': forward_targets[0] if forward_targets else 0,
                'active': forward_targets[1] if forward_targets else 0
            }
        },
        'flow_types': flow_type_summary,
        'top_talkers': top_talkers_summary,
        'top_destinations': top_destinations_summary,
        'protocols': protocol_summary,
        'hourly_distribution': hourly_summary,
        'time_series': time_series_summary
    }
    
    return jsonify(response), 200

@api_bp.route('/api/flows', methods=['GET'])
def api_flows():
    """Get flow data with filtering options"""
    from models import FlowData
    
    # Get query parameters
    start_date = request.args.get('start_date', 
                                 (datetime.utcnow() - timedelta(hours=1)).isoformat())
    end_date = request.args.get('end_date', datetime.utcnow().isoformat())
    device_id = request.args.get('device_id', None, type=int)
    src_ip = request.args.get('src_ip', None)
    dst_ip = request.args.get('dst_ip', None)
    protocol = request.args.get('protocol', None, type=int)
    limit = request.args.get('limit', 1000, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Convert to datetime if they're strings
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date)
    
    # Build query
    query = db.session.query(FlowData).filter(
        FlowData.timestamp.between(start_date, end_date)
    )
    
    # Apply filters
    if device_id:
        query = query.filter(FlowData.device_id == device_id)
    if src_ip:
        query = query.filter(FlowData.src_ip == src_ip)
    if dst_ip:
        query = query.filter(FlowData.dst_ip == dst_ip)
    if protocol:
        query = query.filter(FlowData.protocol == protocol)
    
    # Get total count (for pagination)
    total_count = query.count()
    
    # Apply limit and offset
    query = query.order_by(desc(FlowData.timestamp)).limit(limit).offset(offset)
    
    # Execute query
    flows = query.all()
    
    # Format response
    flow_list = []
    for flow in flows:
        flow_list.append({
            'id': flow.id,
            'device_id': flow.device_id,
            'timestamp': flow.timestamp.isoformat(),
            'src_ip': flow.src_ip,
            'dst_ip': flow.dst_ip,
            'src_port': flow.src_port,
            'dst_port': flow.dst_port,
            'protocol': flow.protocol,
            'protocol_name': get_protocol_name(flow.protocol),
            'bytes': flow.bytes,
            'packets': flow.packets,
            'flow_type': flow.flow_type,
            'tos': flow.tos,
            'tcp_flags': flow.tcp_flags,
            'duration': flow.duration
        })
    
    # Build response
    response = {
        'meta': {
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'time_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'filters': {
                'device_id': device_id,
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'protocol': protocol
            }
        },
        'flows': flow_list
    }
    
    return jsonify(response), 200

@api_bp.route('/api/devices', methods=['GET'])
def api_devices():
    """Get all devices"""
    from models import FlowData, Device
    
    # Get active status filter
    active_only = request.args.get('active', False, type=bool)
    
    # Build query
    query = db.session.query(Device)
    
    # Apply active filter if requested
    if active_only:
        # Only show devices with activity in the last 24 hours
        active_cutoff = datetime.utcnow() - timedelta(hours=24)
        query = query.filter(Device.last_seen >= active_cutoff)
    
    # Execute query
    devices = query.all()
    
    # Format response
    device_list = []
    for device in devices:
        # Get flow count for this device
        flow_count = db.session.query(func.count(FlowData.id)).filter(
            FlowData.device_id == device.id
        ).scalar()
        
        # Get first and last flow timestamps
        first_flow = db.session.query(func.min(FlowData.timestamp)).filter(
            FlowData.device_id == device.id
        ).scalar()
        
        last_flow = db.session.query(func.max(FlowData.timestamp)).filter(
            FlowData.device_id == device.id
        ).scalar()
        
        # Format device info
        device_info = {
            'id': device.id,
            'ip_address': device.ip_address,
            'hostname': device.hostname,
            'description': device.description,
            'flow_type': device.flow_type,
            'flow_version': device.flow_version,
            'first_seen': device.first_seen.isoformat() if device.first_seen else None,
            'last_seen': device.last_seen.isoformat() if device.last_seen else None,
            'flow_count': flow_count,
            'first_flow': first_flow.isoformat() if first_flow else None,
            'last_flow': last_flow.isoformat() if last_flow else None,
            'vendor': device.vendor,
            'model': device.model,
            'os_version': device.os_version,
            'uptime': device.uptime
        }
        
        device_list.append(device_info)
    
    # Build response
    response = {
        'count': len(device_list),
        'devices': device_list
    }
    
    return jsonify(response), 200

@api_bp.route('/api/device/<int:device_id>', methods=['GET'])
def api_device(device_id):
    """Get detail for a specific device"""
    from models import FlowData, Device
    
    # Get the device
    device = db.session.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Get statistics for this device
    # Get flow count
    flow_count = db.session.query(func.count(FlowData.id)).filter(
        FlowData.device_id == device_id
    ).scalar()
    
    # Get first and last flow timestamps
    first_flow = db.session.query(func.min(FlowData.timestamp)).filter(
        FlowData.device_id == device_id
    ).scalar()
    
    last_flow = db.session.query(func.max(FlowData.timestamp)).filter(
        FlowData.device_id == device_id
    ).scalar()
    
    # Get flow types
    flow_types = db.session.query(
        FlowData.flow_type,
        func.count(FlowData.id)
    ).filter(
        FlowData.device_id == device_id
    ).group_by(FlowData.flow_type).all()
    
    # Format flow types
    flow_type_summary = {}
    for flow_type, count in flow_types:
        flow_type_summary[flow_type] = count
    
    # Get recent flows
    recent_flows = db.session.query(FlowData).filter(
        FlowData.device_id == device_id
    ).order_by(desc(FlowData.timestamp)).limit(10).all()
    
    # Format recent flows
    recent_flow_list = []
    for flow in recent_flows:
        recent_flow_list.append({
            'id': flow.id,
            'timestamp': flow.timestamp.isoformat(),
            'src_ip': flow.src_ip,
            'dst_ip': flow.dst_ip,
            'src_port': flow.src_port,
            'dst_port': flow.dst_port,
            'protocol': flow.protocol,
            'protocol_name': get_protocol_name(flow.protocol),
            'bytes': flow.bytes,
            'packets': flow.packets,
            'flow_type': flow.flow_type
        })
    
    # Get time series data (last 24 hours in 1-hour intervals)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    time_series = db.session.query(
        func.date_trunc('hour', FlowData.timestamp).label('hour'),
        func.sum(FlowData.bytes).label('bytes'),
        func.sum(FlowData.packets).label('packets'),
        func.count(FlowData.id).label('flows')
    ).filter(
        FlowData.device_id == device_id,
        FlowData.timestamp.between(start_time, end_time)
    ).group_by('hour').order_by('hour').all()
    
    # Format time series
    time_series_data = []
    for hour, bytes, packets, flows in time_series:
        time_series_data.append({
            'timestamp': hour.isoformat(),
            'bytes': bytes,
            'packets': packets,
            'flows': flows
        })
    
    # Get top talkers
    top_talkers = db.session.query(
        FlowData.src_ip,
        func.sum(FlowData.bytes).label('total_bytes'),
        func.count(FlowData.id).label('flow_count')
    ).filter(
        FlowData.device_id == device_id
    ).group_by(FlowData.src_ip).order_by(desc('total_bytes')).limit(5).all()
    
    # Format top talkers
    top_talkers_list = []
    for ip, bytes, count in top_talkers:
        top_talkers_list.append({
            'ip': ip,
            'bytes': bytes,
            'flow_count': count
        })
    
    # Get top destinations
    top_destinations = db.session.query(
        FlowData.dst_ip,
        func.sum(FlowData.bytes).label('total_bytes'),
        func.count(FlowData.id).label('flow_count')
    ).filter(
        FlowData.device_id == device_id
    ).group_by(FlowData.dst_ip).order_by(desc('total_bytes')).limit(5).all()
    
    # Format top destinations
    top_destinations_list = []
    for ip, bytes, count in top_destinations:
        top_destinations_list.append({
            'ip': ip,
            'bytes': bytes,
            'flow_count': count
        })
    
    # Compile device info
    device_info = {
        'id': device.id,
        'ip_address': device.ip_address,
        'hostname': device.hostname,
        'description': device.description,
        'flow_type': device.flow_type,
        'flow_version': device.flow_version,
        'first_seen': device.first_seen.isoformat() if device.first_seen else None,
        'last_seen': device.last_seen.isoformat() if device.last_seen else None,
        'vendor': device.vendor,
        'model': device.model,
        'os_version': device.os_version,
        'uptime': device.uptime,
        'statistics': {
            'flow_count': flow_count,
            'first_flow': first_flow.isoformat() if first_flow else None,
            'last_flow': last_flow.isoformat() if last_flow else None,
            'flow_types': flow_type_summary
        },
        'recent_flows': recent_flow_list,
        'time_series': time_series_data,
        'top_talkers': top_talkers_list,
        'top_destinations': top_destinations_list
    }
    
    return jsonify(device_info), 200

@api_bp.route('/api/ai/insights/<int:device_id>', methods=['GET'])
def api_ai_insights(device_id):
    """Get AI insights for a specific device"""
    from models import Device
    
    # Get the device
    device = db.session.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Get time window parameters
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)
    
    # Convert to datetime if they're strings
    if start_date and isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)
    if end_date and isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date)
    
    # Create time window if provided
    time_window = None
    if start_date or end_date:
        time_window = {}
        if start_date:
            time_window['start'] = start_date
        if end_date:
            time_window['end'] = end_date
    
    # Get AI insights
    ai_manager = get_ai_insights_manager()
    insights = ai_manager.analyze_device_data(device_id, time_window)
    
    # Add device info
    insights['device'] = {
        'id': device.id,
        'ip_address': device.ip_address,
        'hostname': device.hostname,
        'description': device.description,
        'flow_type': device.flow_type,
        'flow_version': device.flow_version
    }
    
    # Add timestamp
    insights['timestamp'] = datetime.utcnow().isoformat()
    
    return jsonify(insights), 200

@api_bp.route('/api/ai/anomalies', methods=['GET'])
def api_anomalies():
    """Get recent anomalies across all devices"""
    # Get limit parameter
    limit = request.args.get('limit', 10, type=int)
    
    # Get AI insights manager
    ai_manager = get_ai_insights_manager()
    anomalies = ai_manager.get_recent_anomalies(limit)
    
    # Add device info to each anomaly
    for anomaly in anomalies:
        device_id = anomaly.get('device_id')
        if device_id:
            device = db.session.query(Device).filter(Device.id == device_id).first()
            if device:
                anomaly['device'] = {
                    'id': device.id,
                    'ip_address': device.ip_address,
                    'hostname': device.hostname,
                    'description': device.description
                }
    
    # Build response
    response = {
        'count': len(anomalies),
        'anomalies': anomalies
    }
    
    return jsonify(response), 200

def get_protocol_name(protocol_number):
    """Convert protocol number to name"""
    if protocol_number is None:
        return 'Unknown'
    
    protocols = {
        1: 'ICMP',
        6: 'TCP',
        17: 'UDP',
        47: 'GRE',
        50: 'ESP',
        51: 'AH',
        58: 'ICMPv6',
        89: 'OSPF',
        132: 'SCTP'
    }
    
    return protocols.get(protocol_number, f'Protocol {protocol_number}')