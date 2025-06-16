from flask import Blueprint, render_template, request, jsonify, abort, flash, redirect, url_for
from flask_login import login_required, current_user
import json
from datetime import datetime

from models import Organization, Site, Device
from app import db

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/customers')
@login_required
def index():
    """Show the customers dashboard"""
    # Get organizations for the current user
    organizations = current_user.organizations
    
    # Get all sites for these organizations
    sites = []
    for org in organizations:
        org_sites = Site.query.filter_by(organization_id=org.id).all()
        sites.extend(org_sites)
    
    return render_template('customers.html', 
                          organizations=organizations,
                          sites=sites)

@customers_bp.route('/customers/organizations')
@login_required
def organizations():
    """Show organizations page"""
    # Get organizations for the current user
    organizations = current_user.organizations
    
    return render_template('organizations.html', organizations=organizations)

@customers_bp.route('/customers/organizations/<int:org_id>')
@login_required
def organization_details(org_id):
    """Show organization details page"""
    # Get the organization
    organization = Organization.query.get_or_404(org_id)
    
    # Check if user has access to this organization
    if organization not in current_user.organizations:
        abort(403)
    
    # Get sites for this organization
    sites = Site.query.filter_by(organization_id=organization.id).all()
    
    return render_template('organization_details.html', 
                          organization=organization,
                          sites=sites)

@customers_bp.route('/customers/sites')
@login_required
def sites():
    """Show sites page"""
    # Get organizations for the current user
    organizations = current_user.organizations
    org_ids = [org.id for org in organizations]
    
    # Get sites for these organizations
    sites = Site.query.filter(Site.organization_id.in_(org_ids)).all()
    
    return render_template('sites.html', sites=sites, organizations=organizations)

@customers_bp.route('/customers/sites/<int:site_id>')
@login_required
def site_details(site_id):
    """Show site details page"""
    # Get the site
    site = Site.query.get_or_404(site_id)
    
    # Check if user has access to this site's organization
    if site.organization not in current_user.organizations:
        abort(403)
    
    # Get devices for this site
    devices = Device.query.filter_by(site_id=site.id).all()
    
    return render_template('site_details.html', 
                          site=site,
                          devices=devices)

@customers_bp.route('/customers/devices')
@login_required
def devices():
    """Show devices page"""
    # Get organizations for the current user
    organizations = current_user.organizations
    org_ids = [org.id for org in organizations]
    
    # Get sites for these organizations
    sites = Site.query.filter(Site.organization_id.in_(org_ids)).all()
    site_ids = [site.id for site in sites]
    
    # Get devices for these sites
    devices = Device.query.filter(Device.site_id.in_(site_ids)).all()
    
    return render_template('devices.html', devices=devices, sites=sites)

@customers_bp.route('/customers/devices/<int:device_id>')
@login_required
def device_details(device_id):
    """Show device details page"""
    # Get the device
    device = Device.query.get_or_404(device_id)
    
    # Check if user has access to this device's site's organization
    if device.site.organization not in current_user.organizations:
        abort(403)
    
    return render_template('device_details.html', device=device)

# API endpoints for CRUD operations

@customers_bp.route('/api/organizations', methods=['POST'])
@login_required
def api_create_organization():
    """API endpoint to create a new organization"""
    data = request.json
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Organization name is required'}), 400
    
    # Create organization
    organization = Organization(
        name=data.get('name'),
        description=data.get('description'),
        is_msp=data.get('is_msp', False)
    )
    
    # Add current user to organization
    organization.users.append(current_user)
    
    db.session.add(organization)
    db.session.commit()
    
    return jsonify({
        'id': organization.id,
        'name': organization.name,
        'status': 'created'
    })

@customers_bp.route('/api/organizations/<int:org_id>', methods=['PUT'])
@login_required
def api_update_organization(org_id):
    """API endpoint to update an organization"""
    organization = Organization.query.get_or_404(org_id)
    
    # Check access
    if organization not in current_user.organizations:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.json
    
    # Update fields
    if 'name' in data:
        organization.name = data['name']
    
    if 'description' in data:
        organization.description = data['description']
    
    if 'is_msp' in data:
        organization.is_msp = data['is_msp']
    
    db.session.commit()
    
    return jsonify({
        'id': organization.id,
        'name': organization.name,
        'status': 'updated'
    })

@customers_bp.route('/api/sites', methods=['POST'])
@login_required
def api_create_site():
    """API endpoint to create a new site"""
    data = request.json
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Site name is required'}), 400
    
    if not data.get('organization_id'):
        return jsonify({'error': 'Organization ID is required'}), 400
    
    # Check access to organization
    org_id = data.get('organization_id')
    organization = Organization.query.get_or_404(org_id)
    
    if organization not in current_user.organizations:
        return jsonify({'error': 'Permission denied'}), 403
    
    # Create site
    site = Site(
        name=data.get('name'),
        description=data.get('description'),
        address=data.get('address'),
        contact_info=data.get('contact_info'),
        organization_id=org_id
    )
    
    db.session.add(site)
    db.session.commit()
    
    return jsonify({
        'id': site.id,
        'name': site.name,
        'status': 'created'
    })

@customers_bp.route('/api/sites/<int:site_id>', methods=['PUT'])
@login_required
def api_update_site(site_id):
    """API endpoint to update a site"""
    site = Site.query.get_or_404(site_id)
    
    # Check access
    if site.organization not in current_user.organizations:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.json
    
    # Update fields
    if 'name' in data:
        site.name = data['name']
    
    if 'description' in data:
        site.description = data['description']
    
    if 'address' in data:
        site.address = data['address']
    
    if 'contact_info' in data:
        site.contact_info = data['contact_info']
    
    db.session.commit()
    
    return jsonify({
        'id': site.id,
        'name': site.name,
        'status': 'updated'
    })

@customers_bp.route('/api/devices', methods=['POST'])
@login_required
def api_create_device():
    """API endpoint to create a new device"""
    data = request.json
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Device name is required'}), 400
    
    if not data.get('ip_address'):
        return jsonify({'error': 'IP address is required'}), 400
    
    if not data.get('site_id'):
        return jsonify({'error': 'Site ID is required'}), 400
    
    # Check access to site
    site_id = data.get('site_id')
    site = Site.query.get_or_404(site_id)
    
    if site.organization not in current_user.organizations:
        return jsonify({'error': 'Permission denied'}), 403
    
    # Create device
    device = Device(
        name=data.get('name'),
        ip_address=data.get('ip_address'),
        device_type=data.get('device_type'),
        os_type=data.get('os_type'),
        os_version=data.get('os_version'),
        description=data.get('description'),
        site_id=site_id
    )
    
    db.session.add(device)
    db.session.commit()
    
    return jsonify({
        'id': device.id,
        'name': device.name,
        'status': 'created'
    })

@customers_bp.route('/api/devices/<int:device_id>', methods=['PUT'])
@login_required
def api_update_device(device_id):
    """API endpoint to update a device"""
    device = Device.query.get_or_404(device_id)
    
    # Check access
    if device.site.organization not in current_user.organizations:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.json
    
    # Update fields
    if 'name' in data:
        device.name = data['name']
    
    if 'ip_address' in data:
        device.ip_address = data['ip_address']
    
    if 'device_type' in data:
        device.device_type = data['device_type']
    
    if 'os_type' in data:
        device.os_type = data['os_type']
    
    if 'os_version' in data:
        device.os_version = data['os_version']
    
    if 'description' in data:
        device.description = data['description']
    
    db.session.commit()
    
    return jsonify({
        'id': device.id,
        'name': device.name,
        'status': 'updated'
    })

# API endpoints to get single items for editing

@customers_bp.route('/api/organizations/<int:org_id>', methods=['GET'])
@login_required
def api_get_organization(org_id):
    """API endpoint to get a single organization"""
    organization = Organization.query.get_or_404(org_id)
    
    # Check access
    if organization not in current_user.organizations:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'id': organization.id,
        'name': organization.name,
        'description': organization.description,
        'is_msp': organization.is_msp,
        'created_at': organization.created_at.isoformat()
    })

@customers_bp.route('/api/sites/<int:site_id>', methods=['GET'])
@login_required
def api_get_site(site_id):
    """API endpoint to get a single site"""
    site = Site.query.get_or_404(site_id)
    
    # Check access
    if site.organization not in current_user.organizations:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'id': site.id,
        'name': site.name,
        'description': site.description,
        'address': site.address,
        'contact_info': site.contact_info,
        'organization_id': site.organization_id,
        'created_at': site.created_at.isoformat()
    })

@customers_bp.route('/api/devices/<int:device_id>', methods=['GET'])
@login_required
def api_get_device(device_id):
    """API endpoint to get a single device"""
    device = Device.query.get_or_404(device_id)
    
    # Check access
    if device.site.organization not in current_user.organizations:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'id': device.id,
        'name': device.name,
        'ip_address': device.ip_address,
        'device_type': device.device_type,
        'os_type': device.os_type,
        'os_version': device.os_version,
        'description': device.description,
        'site_id': device.site_id,
        'created_at': device.created_at.isoformat()
    })

@customers_bp.route('/api/devices/<int:device_id>/monitoring', methods=['POST'])
@login_required
def api_configure_device_monitoring(device_id):
    """API endpoint to configure monitoring for a device"""
    device = Device.query.get_or_404(device_id)
    
    # Check access
    if device.site.organization not in current_user.organizations:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.json
    
    # In a real implementation, this would configure collectors
    # and update some device monitoring settings table
    
    # For now, just return success
    return jsonify({
        'id': device.id,
        'name': device.name,
        'status': 'configured',
        'message': 'Monitoring configuration updated successfully'
    })

@customers_bp.route('/api/devices/<int:device_id>', methods=['DELETE'])
@login_required
def api_delete_device(device_id):
    """API endpoint to delete a device"""
    device = Device.query.get_or_404(device_id)
    
    # Check access
    if device.site.organization not in current_user.organizations:
        return jsonify({'error': 'Permission denied'}), 403
    
    # Get device info for response
    device_name = device.name
    
    # Delete the device
    db.session.delete(device)
    db.session.commit()
    
    return jsonify({
        'status': 'deleted',
        'message': f'Device {device_name} deleted successfully'
    })